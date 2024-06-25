# type: ignore
# ruff: noqa
# a = 1


# def f(a) -> None: ...


# def ff() -> None:
#     pass


# def fff() -> None:
#     global a
#     a = 2
def t(d, ed=1, de: int=2, *ded, **deed):
    global a, b
    nonlocal c, d

    from typing import List, Dict as dictt
    from typing import Self
    import os as as_

    a = 1
    a = (b := 3)
    (oh, ah) = 1, 2

    async with f as ac:
        ...

    with f as ab:
        ...

    for a in f:
        ...

    async for oms in f:
        ...

    while a := f:
        ...

    if a := f:
        ...

    def ff(a):
        a = 2
        if a := 111:
            ...

    class C:
        c = 2

    def ffff(a=1): ...

    def fffff(a: int = 1): ...
    def fffff(a: int): ...
    def fffff(*a: int): ...
    def fffff(*a): ...
    def fffff(**a: int): ...
    def fffff(**a): ...

    match b:
        case Ty(u=abud):
            ...
        case {"me": abc, **dargs}:
            ...
        case [a, d]:
            ...
        case a as bbb:
            ...
        case a:
            ...

    await a
