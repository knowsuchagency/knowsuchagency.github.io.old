import json
from pathlib import Path
from typing import *
import threading

import nbformat
from nbconvert import MarkdownExporter
from nbconvert.preprocessors import Preprocessor

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from traitlets.config import Config

from fabric.api import *


@task
def render_notebooks():
    """Render jupyter notebooks to markdown"""
    notebooks = Path('notebooks').glob('*.ipynb')
    for notebook in notebooks:
        write_jupyter_to_md(notebook)


@task
def serve():
    """Watch for changes in jupyter notebooks and render them anew while hugo runs"""
    stop_observing = threading.Event()
    notebook_observation_thread = threading.Thread(
        target=observe_notebooks,
        args=(stop_observing,)
    )
    notebook_observation_thread.start()
    local('hugo serve')
    stop_observing.set()

@task
def publish():
    """Publish notebook to github pages"""

    with settings(warn_only=True):
        if local('git diff-index --quiet HEAD --').failed:
            local('git status')
            abort('The working directory is dirty. Please commit any pending changes.')

    # deleting old publication
    local('rm -rf public')
    local('mkdir public')
    local('git worktree prune')
    local('rm -rf .git/worktrees/public/')
    # checkout out gh-pages branch into public
    local('git worktree add -B master public upstream/master')
    # removing existing files
    local('rm -rf public/*')
    # generating site
    render_notebooks()
    local('hugo')
    # push to github
    with lcd('public'), settings(warn_only=True):
        local('git add .')
        local('git commit -m "Committing to master (Fabfile)"')
    # push to master
    local('git push upstream master')
    print('push succeeded')


class CustomPreprocessor(Preprocessor):
    def preprocess(self, nb, resources):
        """
        Remove blank cells
        """
        for index, cell in enumerate(nb.cells):
            if cell.cell_type == 'code' and (not cell.outputs or not cell.source):
                nb.cells.pop(index)
                continue
            nb.cells[index], resources = self.preprocess_cell(cell, resources, index)
        return nb, resources

    def preprocess_cell(self, cell, resources, cell_index):
        """
        Remove extraneous whitespace from code cells' source code
        """
        if cell.cell_type == 'code':
            cell.source = cell.source.strip()

        return cell, resources


def convert_notebook_to_hugo_markdown(path: Union[Path, str]) -> str:
    with open(Path(path)) as fp:
        notebook = nbformat.read(fp, as_version=4)

        assert 'front-matter' in notebook['metadata'], "You must have a front-matter field in the notebook's metadata"
        front_matter_dict = dict(notebook['metadata']['front-matter'])
        front_matter = json.dumps(front_matter_dict, indent=2)

    c = Config()
    c.MarkdownExporter.preprocessors = [CustomPreprocessor]
    markdown_exporter = MarkdownExporter(config=c)

    markdown, _ = markdown_exporter.from_notebook_node(notebook)

    output = '\n'.join(('---', front_matter, '---', '<!--more-->', markdown))

    return output


def write_jupyter_to_md(notebook):
    notebook = Path(notebook)
    hugo_markdown = convert_notebook_to_hugo_markdown(notebook)
    hugo_file = Path('content/post/', notebook.stem + '.md')
    hugo_file.write_text(hugo_markdown)
    print(notebook.name, '->', hugo_file.name)


class NotebookHandler(PatternMatchingEventHandler):
    patterns = ["*.ipynb"]

    def process(self, event):
        write_jupyter_to_md(event.src_path)

    def on_modified(self, event):
        self.process(event)

    def on_created(self, event):
        self.process(event)


def observe_notebooks(event):
    """Write notebooks to markdown files until event is set."""
    observer = Observer()
    observer.schedule(NotebookHandler(), 'notebooks')
    observer.start()

    if event.is_set():
        observer.stop()
        observer.join()
