#!/usr/bin/env python3
import json
import os
import re
import shlex
import subprocess as sp
import sys
import types
from collections import defaultdict
from datetime import datetime
from functools import singledispatch, wraps
from pathlib import Path
from typing import *

import click
import crayons
import nbformat
from nbconvert import MarkdownExporter
from nbconvert.preprocessors import Preprocessor
from shell_utils import shell, cd
from traitlets.config import Config
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer


@singledispatch
def notify(message: str, title='run.py', sound=None):
    """Mac os pop-up notification."""
    sound_arg = '' if sound is None else '--sound ' + sound
    shell(f'notify --title {title} {sound_arg} {message}',
          capture=True, show_command=False)


@notify.register(types.FunctionType)
def _(func):
    """
    Send notification that task has finished.

    Especially useful for long-running tasks
    """

    @wraps(func)
    def inner(*args, **kwargs):
        result = None
        message = 'Succeeded!'

        try:
            result = func(*args, **kwargs)
        except Exception:
            message = 'Failed'
            raise
        else:
            return result
        finally:
            notify(message, title=getattr(func, '__name__'))

    return inner


@click.group()
def main():
    """
    Development tasks for shell-utils
    """

    # ensure we're running commands from project root

    root = Path(__file__).parent.absolute()
    cwd = Path().absolute()

    if root != cwd:
        click.secho(f'Navigating from {cwd} to {root}',
                    fg='yellow')
        os.chdir(root)

    if root != cwd:
        click.secho(f'Navigating from {cwd} to {root}', fg='yellow')
        os.chdir(root)


def update_notebooks_metadata():
    """Update all the notebooks' metadata fields."""
    notebooks = Path('notebooks').glob('*.ipynb')
    for notebook in notebooks:
        if (not str(notebook).startswith('.')) and ('untitled' not in str(notebook).lower()):
            yield update_notebook_metadata(notebook)


@main.command()
def render_notebooks():
    """
    Render jupyter notebooks it notebooks directory to respective markdown in content/post directory.
    """
    for notebook in update_notebooks_metadata():
        write_hugo_formatted_nb_to_md(notebook)


def serve(hugo_args='', init_jupyter=True):
    """
    Watch for changes in jupyter notebooks and render them anew while hugo runs.

    Args:
        init_jupyter: initialize jupyter if set to True
        hugo_args: command-line arguments to be passed to `hugo server`
    """
    observer = Observer()
    observer.schedule(NotebookHandler(), 'notebooks')
    observer.start()

    hugo_process = sp.Popen(('hugo', 'serve', *shlex.split(hugo_args)))

    if init_jupyter:
        jupyter_process = sp.Popen(('jupyter', 'notebook'), cwd='notebooks')

    shell('open http://localhost:1313')

    try:
        print(crayons.green('Successfully initialized server(s)'),
              crayons.yellow('press ctrl+C at any time to quit'),
              )
        while True:
            pass
    except KeyboardInterrupt:
        print(crayons.yellow('Terminating'))
    finally:
        if init_jupyter:
            print(crayons.yellow('shutting down jupyter'))
            jupyter_process.kill()

        print(crayons.yellow('shutting down watchdog'))
        observer.stop()
        observer.join()
        print(crayons.yellow('shutting down hugo'))
        hugo_process.kill()
        print(crayons.green('all processes shut down successfully'))
        sys.exit(0)


@main.command()
def publish():
    """
    Publish notebook to github pages.

    Assumes this is yourusername.github.io repo aka
    User Pages site as described in
    https://help.github.com/articles/user-organization-and-project-pages/
    and that you're using the master branch only
    to have the rendered content of your blog.
    """
    if shell('git diff-index --quiet HEAD --', check=False).returncode:
        shell('git status')
        click.secho('The working directory is dirty. Please commit any pending changes.', fg='red')

    # deleting old publication
    shell('rm -rf public')
    shell('mkdir public')
    shell('git worktree prune')
    shell('rm -rf .git/worktrees/public/')

    # checkout out master branch into public
    shell('git worktree add -B master public upstream/master')

    # removing any existing files
    shell('rm -rf public/*')

    # generating site
    with click.get_current_context() as ctx:
        ctx.invoke(render_notebooks)
    shell('hugo')

    # commit
    with cd('public'):
        shell('git add .', check=False)
        shell('git commit -m "Committing to master (Fabfile)"', check=False)

    # push to master
    shell('git push upstream master')
    print('push succeeded')


########## Jupyter stuff #################

class CustomPreprocessor(Preprocessor):
    """Remove blank code cells and unnecessary whitespace."""

    def preprocess(self, nb, resources):
        """
        Remove blank cells
        """
        for index, cell in enumerate(nb.cells):
            if cell.cell_type == 'code' and not cell.source:
                nb.cells.pop(index)
            else:
                nb.cells[index], resources = self.preprocess_cell(cell, resources, index)
        return nb, resources

    def preprocess_cell(self, cell, resources, cell_index):
        """
        Remove extraneous whitespace from code cells' source code
        """
        if cell.cell_type == 'code':
            cell.source = cell.source.strip()

        return cell, resources


def doctor(string: str) -> str:
    """Get rid of all the wacky newlines nbconvert adds to markdown output and return result."""
    post_code_newlines_patt = re.compile(r'(```)(\n+)')
    inter_output_newlines_patt = re.compile(r'(\s{4}\S+)(\n+)(\s{4})')

    post_code_filtered = re.sub(post_code_newlines_patt, r'\1\n\n', string)
    inter_output_filtered = re.sub(inter_output_newlines_patt, r'\1\n\3', post_code_filtered)

    return inter_output_filtered


def notebook_to_markdown(path: Union[Path, str]) -> str:
    """
    Convert jupyter notebook to hugo-formatted markdown string

    Args:
        path: path to notebook

    Returns: hugo-formatted markdown

    """
    # first, update the notebook's metadata
    update_notebook_metadata(path)

    with open(Path(path)) as fp:
        notebook = nbformat.read(fp, as_version=4)
        assert 'front-matter' in notebook['metadata'], "You must have a front-matter field in the notebook's metadata"
        front_matter_dict = dict(notebook['metadata']['front-matter'])
        front_matter = json.dumps(front_matter_dict, indent=2)

    c = Config()
    c.MarkdownExporter.preprocessors = [CustomPreprocessor]
    markdown_exporter = MarkdownExporter(config=c)

    markdown, _ = markdown_exporter.from_notebook_node(notebook)
    doctored_md = doctor(markdown)
    # added <!--more--> comment to prevent summary creation
    output = '\n'.join(('---', front_matter, '---', '<!--more-->', doctored_md))

    return output


def write_hugo_formatted_nb_to_md(notebook: Union[Path, str], render_to: Optional[Union[Path, str]] = None) -> Path:
    """
    Convert Jupyter notebook to markdown and write it to the appropriate file.

    Args:
        notebook: The path to the notebook to be rendered
        render_to: The directory we want to render the notebook to
    """
    notebook = Path(notebook)
    notebook_metadata = json.loads(notebook.read_text())['metadata']
    rendered_markdown_string = notebook_to_markdown(notebook)
    slug = notebook_metadata['front-matter']['slug']
    render_to = render_to or notebook_metadata['hugo-jupyter']['render-to'] or 'content/post/'

    if not render_to.endswith('/'):
        render_to += '/'

    rendered_markdown_file = Path(render_to, slug + '.md')

    if not rendered_markdown_file.parent.exists():
        rendered_markdown_file.parent.mkdir(parents=True)

    rendered_markdown_file.write_text(rendered_markdown_string)
    print(notebook.name, '->', rendered_markdown_file.name)
    return rendered_markdown_file


def update_notebook_metadata(notebook: Union[Path, str],
                             title: Union[None, str] = None,
                             subtitle: Union[None, str] = None,
                             date: Union[None, str] = None,
                             slug: Union[None, str] = None,
                             render_to: str = None) -> Path:
    """
    Update the notebook's metadata for hugo rendering

    Args:
        notebook: notebook to have edited
    """
    notebook_path: Path = Path(notebook)
    notebook_data: dict = json.loads(notebook_path.read_text())
    old_front_matter: dict = notebook_data.get('metadata', {}).get('front-matter', {})

    # generate front-matter fields
    title = title or old_front_matter.get('title') or notebook_path.stem
    subtitle = subtitle or old_front_matter.get('subtitle') or 'Generic subtitle'
    date = date or old_front_matter.get('date') or datetime.now().strftime('%Y-%m-%d')
    slug = slug or old_front_matter.get('slug') or title.lower().replace(' ', '-')

    front_matter = {
        'title': title,
        'subtitle': subtitle,
        'date': date,
        'slug': slug,
    }

    # update front-matter
    notebook_data['metadata']['front-matter'] = front_matter

    # update hugo-jupyter settings
    render_to = render_to or notebook_data['metadata'].get('hugo-jupyter', {}).get('render-to') or 'content/post/'
    hugo_jupyter = {
        'render-to': render_to
    }
    notebook_data['metadata']['hugo-jupyter'] = hugo_jupyter

    # write over old notebook with new front-matter
    notebook_path.write_text(json.dumps(notebook_data))

    # make the notebook trusted again, now that we've changed it
    sp.run(['jupyter', 'trust', str(notebook_path)])

    return notebook_path


########## Watchdog stuff #################

class NotebookHandler(PatternMatchingEventHandler):
    patterns = ["*.ipynb"]

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        # a mapping of notebook filepaths and their respective metadata
        self.notebook_metadata: Mapping[str, dict] = {}
        # a mapping of notebook filepaths and where they were rendered to
        self.notebook_render: Mapping[str, Set[Path]] = defaultdict(set)

    def process(self, event):
        try:
            # don't automatically update front matter
            # and render notebook until filename is
            # changed from untitled...
            if 'untitled' not in event.src_path.lower() and '.~' not in event.src_path:
                self.delete_notebook_md(event)

                # if not self.notebook_metadata.get(event.src_path):
                #     self.update_notebook_metadata_registry(event.src_path)

                # update metadata registry
                self.update_notebook_metadata_registry(event)

                render_to = self.get_render_to_field(event)

                rendered = write_hugo_formatted_nb_to_md(event.src_path, render_to=render_to)

                self.notebook_render[event.src_path].add(rendered)

        except Exception as e:
            print('could not successfully render', event.src_path)
            print(e)

    def on_modified(self, event):
        self.process(event)

    def on_created(self, event):
        # update notebook metadata as appropriate
        update_notebook_metadata(event.src_path)
        self.process(event)

    def on_deleted(self, event):
        self.delete_notebook_md(event)

    def delete_notebook_md(self, event):
        print(crayons.yellow("attempting to delete the post for {}".format(event.src_path)))
        for path in self.notebook_render[event.src_path]:
            if path.exists():
                path.unlink()
                print(crayons.yellow('removed post: {}'.format(path)))

    def update_notebook_metadata_registry(self, event):
        try:
            self.notebook_metadata[event.src_path] = json.loads(
                Path(event.src_path).read_text())['metadata']
        except json.JSONDecodeError:
            print(crayons.yellow("Could not decode as json file: {}".format(event.src_path)))

    def get_render_to_field(self, event) -> Optional[Path]:
        try:
            return self.notebook_metadata[event.src_path].get('hugo-jupyter', {}).get('render-to')
        except json.JSONDecodeError:
            print(crayons.yellow("could not marshal notebook to json: {}".format(event.src_path)))
        except KeyError:
            print("{} has no field hugo-jupyter.render-to in its metadata".format(event.src_path))


if __name__ == '__main__':
    main()
