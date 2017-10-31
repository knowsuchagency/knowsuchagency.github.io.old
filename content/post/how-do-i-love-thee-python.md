---
{
  "title": "How do I love thee, Python?",
  "subtitle": "Let me count the ways",
  "date": "2017-10-13",
  "slug": "how-do-i-love-thee-python"
}
---
<!--more-->


```python
from functools import partial

@partial(lambda gen: lambda n: list(gen(n)))
def fib(n):
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b
        
fib(8)
```

    [0, 1, 1, 2, 3, 5, 8, 13]


