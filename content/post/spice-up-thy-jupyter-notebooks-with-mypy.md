+++
bigimg = ""
date = "2017-03-19T16:12:36-07:00"
subtitle = ""
title = "Spice up Thy Jupyter Notebooks With mypy"

+++
<!--more-->


# Spice Up Thy Jupyter Notebooks With mypy

I use [Jupyter](http://jupyter.org/) notebooks all the time. I use them to author the content for articles like the one you're reading. I use them to explore data. And I use them whenever I want to prototype standalone modules or learn new programming concepts, since notebooks allow us to quickly iterate on new ideas and provide powerful ways introspect, profile, and debug code - and more. 

Before I continue on my rant, let's quickly take a look at some code to demonstrate what we want to be able to do.

```python
%%typecheck --ignore-missing-imports

from sympy import sympify, init_printing
init_printing()

integer: int
    
integer = "mypy won't like this"

expr = sympify('(e**3)**(1/2)') 

# The following will be pretty printed, not just the last expression
# since the I have configured IPython as such and the typecheck
# magic uses the current profile

expr

5
```
    <string>:7: error: Incompatible types in assignment (expression has type "str", variable has type "int")
$$\sqrt{e^{3}}$$
$$5$$


I've recently become interested in Python's new typing module and [mypy](http://mypy-lang.org/), and I wanted to be able to use them seamlessly in the context of my Jupyter notebooks.

I should mention that Jupyter is an evolution of the original IPython project. I bring this up because I'm going to reference the documentation for IPython, which can be thought of as the the code that enables Python to work with Jupyter. Think of Jupyter as the tooling that allows for us to do all the fancy code editing and visualization browser, and IPython as the compatibility layer between Jupyter and Python. This is a bit simplistic, but hopefully avoids confusion for anyone who isn't intimately familiar with both projects and the genesis of the Jupyter project.

Jupyter has a concept of cell "magics" which allow us to perform helpful functions in the context of a Jupyter shell. For example, when using IPython, the `%pastebin` magic allows us to easily upload bits of code to Github's Gist pastebin, `%pdoc [object]` prints the docstring for a particular object, and `%%latex` renders a block of text as latex.

Magics that start with  '%' apply only to the line that it is written on, while
magics that start with '%%' apply to a block of code proceeding that line.

Jupyter allows us to write our own custom magics, apart from the built-in magics provided. Detailed documentation on how to do that can be found [here](http://ipython.readthedocs.io/en/stable/config/custommagics.html).

Since the custom magics you use depend on how you have IPython configured and what profile you're using, I'm providing the following code in the form of a gist, since distributing it as a package would be finicky as the package would need to attempt to figure out your IPython configuration, a task which seems best left to you, the human.

I'm going to assume that you have Jupyter installed and that you have at least a default profile created. `pip install -U jupyter` will install Jupyter and `ipython profile create` will create a default profile for you if you don't yet have one. This will allow you to use custom magics and configure the way IPython works in various other ways. Once you have a profile created, you can use `ipython locate profile` to find the configuration directory for that profile.

For example, the IPython configuration file for my default profile, 'ipython_config.py' has the following lines

    c.TerminalInteractiveShell.ast_node_interactivity = 'all'
    c.InteractiveShell.ast_node_interactivity = 'all'
    
which tells IPython to print the the repr for any object which has it's own line. 

For example:


```python
foo = 'bar'
bar = 'baz'

foo
bar # normally, only this object is printed
```
    'bar'
    'baz'


I wanted my magic to do 4 things.

1. Run the block of code through mypy and print its output
2. Allow me to alter mypy's behavior, as with the mypy cli
2. Not conflict with the normal behavior of the block of code
3. Run the block of code in the context of my current profile

Though the code it took to do this is really straightforward, it took some digging around in the Jupyter and IPython docs to get it to work as I wanted. Hopefully you find it useful and elucidating.

Without further ado, {{<gist knowsuchagency f7b2203dd613756a45f816d6809f01a6 >}}


