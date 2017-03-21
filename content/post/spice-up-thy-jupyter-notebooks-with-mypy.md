+++
bigimg = ""
date = "2017-03-19T16:12:36-07:00"
subtitle = "Add type-checking to Jupyter Notebook cells"
title = "Spice Up Thy Jupyter Notebooks With mypy"

+++
<!--more-->

I use [Jupyter](http://jupyter.org/) notebooks all the time. I use them to author the content for articles like the one you're reading. I use them to explore data. And I use them whenever I want to prototype standalone modules or learn new programming concepts, since notebooks allow us to quickly iterate on new ideas and provide powerful ways introspect, profile, and debug code - and more. 

I've recently become interested in Python's new typing module and [mypy](http://mypy-lang.org/), and I wanted to be able to use them seamlessly in the context of my Jupyter notebooks. IPython (the project that bridges Jupyter and Python) allows us to alter the behavior of a code cell through the use of ["magics"](http://ipython.readthedocs.io/en/stable/interactive/magics.html?highlight=magic) - lines that begin with % for a single-line magic or %% for magics that work over multiple lines.


So I wanted [my own custom magic](http://ipython.readthedocs.io/en/stable/config/custommagics.html) to do 4 things.

1. Run the block of code through mypy and print its output
2. Allow me to alter mypy's behavior, as with the mypy cli
2. Not conflict with the normal behavior of the block of code
3. Run the block of code in the context of my current profile

Since my IPython configuration file has the following lines

    c.TerminalInteractiveShell.ast_node_interactivity = 'all'
    c.InteractiveShell.ast_node_interactivity = 'all'
    
which tells IPython to print the the repr for any object which has its own line, I want to ensure this behavior is respected by my magic command.

You can find your own IPython configuration file using the command `ipython locate profile`.
If you don't yet have a profile, you can create a default one with `ipython profile create`.

**To demonstrate:**

```python
%%typecheck --ignore-missing-imports

from sympy import sympify, init_printing
init_printing()

integer: int
    
integer = "mypy won't like this"

sympify('(e**3)**(1/2)') 

"Notice the previous line was also pretty-printed"
```
    <string>:7: error: Incompatible types in assignment (expression has type "str", variable has type "int")
$$\sqrt{e^{3}}$$
'Notice the previous line was also pretty-printed'

---

The code it took to do this is really straightforward, but it took some digging around in the Jupyter and IPython docs to get it to work as I wanted. Hopefully you find it useful and elucidating.

Without further ado, {{<gist knowsuchagency f7b2203dd613756a45f816d6809f01a6 >}}


