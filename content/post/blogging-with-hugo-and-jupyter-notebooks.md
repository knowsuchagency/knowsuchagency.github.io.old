---
{
  "title": "Blogging with Hugo and Jupyter Notebooks",
  "subtitle": "Hugo + Jupyter, the easy way",
  "date": "2017-07-10",
  "slug": "blogging-with-hugo-and-jupyter-notebooks"
}
---
<!--more-->

### TL;DR

    cd your_hugo_project_root
    pip install hugo_jupyter
    hugo_jupyter --init
    

----------

### Update (19-July-2017)

Since posting the article, I've created a package on pypi, [hugo_jupyter](https://pypi.org/project/hugo_jupyter/) that automates the creation of the fabfile and notebooks directory at the root of your hugo project.

### What

If you've read my previous posts, you've probably guessed I really, really like [Jupyter notebooks](http://jupyter.org/). I think they're not only a great coding environment - they're also an amazing publishing tool and I wanted to use them as the primary way I write blog posts.

I've used a number of static site generators in the past, namely [Pelican](https://blog.getpelican.com/), [Nikola](https://getnikola.com/), and [Hugo](https://gohugo.io/).

While each of those tools has their strengths and weaknesses (Nikola has first-class support for Jupyter notebooks, for example), Hugo has been my favorite one to use overall.

The problem is that Jupyter notebooks are not yet supported "[out-of-the-box](https://gohugo.io/content/supported-formats/)" by Hugo. While that's something I may look into rectifying myself in the future, I wanted a way to reliably convert my notebooks to markdown for hugo today. Up till now I'd been doing it mostly manually, but I now offer a better solution.

If you haven't yet used or heard of [Fabric](http://www.fabfile.org/), it is my absolute favorite high-level automation tool. Although their intended use-case seems to be automation of tasks on remote machines over ssh (something that more modern and robust tools like [ansible](https://www.ansible.com/) may be better-suited for), I find it to be a perfect way to automate many tasks on my local machine as opposed to shell scripts, Python modules, or Makefiles. The reasons as to why that's true for me are an article for another day, but suffice to say this is the way that we're going to convert our notebooks to markdown for hugo.


### How

This recipe is going to be more helpful if you're hosting your hugo blog your personal github page as described in [their documentation on the subject](https://help.github.com/articles/user-organization-and-project-pages/) i.e. {yourname}.github.io repo and have an src branch where you work as normal and use the master branch only for the rendered website.

The fabfile is still useful even if that isn't the case, but the `publish` command does a lot for you if you're hosting your blog on your personal github page as described.

At minimum, this recipe assumes you have a hugo site already generated as described in [their documentation](https://gohugo.io/overview/quickstart/).

1. Make sure you're using Python 3. You can use a package I wrote to quickly bootstrap your project for use with Jupyter notebooks. ``pip install hugo_jupyter; hugo_jupyter --init``
2. Copy the [fabfile](https://github.com/knowsuchagency/knowsuchagency.github.io/blob/src/fabfile.py) I'm using to generate this same page on my github repo to the root of your hugo project
3. Create a `notebooks` directory in the root of your project where your jupyter notebooks will be.
4. As you create new notebooks, edit the notebook metadata to include the `front-matter` hugo needs to render posts. 

<img src="/img/tut1.png">
<img src="/img/tut2.png">



Fabric and your fabfile.py will then allow you to render notebooks, serve the website on your localhost and have them re-render dynamically update while you edit your notebooks, and publish to github once you're ready.

All you need to do is run the commands from the root of your project i.e.

    fab render_notebooks
    fab serve
    fab publish

