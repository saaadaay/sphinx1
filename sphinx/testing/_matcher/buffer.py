from __future__ import annotations

__all__ = ('Line', 'Block')

import abc
import sys
from collections.abc import Sequence
from itertools import starmap
from typing import TYPE_CHECKING, Generic, TypeVar, final, overload

from sphinx.testing._matcher.util import windowed

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import SupportsIndex

    from typing_extensions import Self

_T = TypeVar('_T', bound=Sequence[str])


class ComparableView(Generic[_T], abc.ABC):
    """A string or a sequence of strings implementing rich comparison.

    :meta private:
    """

    # add __weakref__ to allow the object being weak-referencable
    __slots__ = ('__buffer', '__offset', '__weakref__')

    def __init__(self, buffer: _T, offset: int = 0, /, *, _check: bool = True) -> None:
        if _check and not isinstance(offset, int):
            msg = f'offset must be an integer, got: {offset!r}'
            raise TypeError(msg)

        if _check and offset < 0:
            msg = f'offset must be >= 0, got: {offset!r}'
            raise ValueError(msg)

        self.__buffer = buffer
        self.__offset = offset

    @property
    def buffer(self) -> _T:
        """The internal (immutable) buffer."""
        return self.__buffer

    @property
    def offset(self) -> int:
        """The index of this object in the original source."""
        return self.__offset

    def __copy__(self) -> Self:
        return self.__class__(self.buffer, self.offset, _check=False)

    def __bool__(self) -> bool:
        return bool(len(self))

    def __iter__(self) -> Iterator[str]:
        return iter(self.buffer)

    def __reversed__(self) -> Iterator[str]:
        return reversed(self.buffer)

    def __len__(self) -> int:
        return len(self.buffer)

    def __contains__(self, value: object, /) -> bool:
        return value in self.buffer

    @abc.abstractmethod
    def __lt__(self, other: object, /) -> bool:
        pass

    def __le__(self, other: object, /) -> bool:
        return self == other or self < other

    def __ge__(self, other: object, /) -> bool:
        return self == other or self > other

    @abc.abstractmethod
    def __gt__(self, other: object, /) -> bool:
        pass


@final
class Line(ComparableView[str]):
    """A line found by :meth:`~sphinx.testing.matcher.LineMatcher.match`.

    A :class:`Line` can be compared to :class:`str`, :class:`Line` objects or
    a pair (i.e., a two-length sequence) ``(line, line_offset)`` where

    - *line* is a native :class:`str` (not a subclass thereof), and
    - *line_offset* is an nonnegative integer.

    By convention, the comparison result (except for ``!=``) of :class:`Line`
    objects with distinct :attr:`offset` is always ``False``. Use :class:`str`
    objects instead if the offset is not relevant.
    """

    def __init__(self, line: str = '', offset: int = 0, /, *, _check: bool = True) -> None:
        """Construct a :class:`Line` object.

        The *line* must be a native :class:`str` object.
        """
        if _check and type(line) is not str:
            # force the line to be a true string and not another string-like
            msg = f'expecting a native string, got: {line!r}'
            raise TypeError(msg)

        super().__init__(line, offset, _check=_check)

    @classmethod
    def view(cls, index: int, line: object, /) -> Self:
        """Alternative constructor flipping the order of the arguments.

        This is typically useful with :func:`enumerate`, namely this makes::

            from itertools import starmap
            lines = list(starmap(Line.view, enumerate(src))

        equivalent to::

            lines = [Line(str(line), index) for index, line in enumerate(src)]
        """
        return cls(str(line), index, _check=True)

    # dunder methods

    def __str__(self) -> str:
        """The line as a string."""
        return self.buffer

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self!s}, offset={self.offset})'

    def __getitem__(self, index: int | slice, /) -> str:
        """Return the *nth* character."""
        return self.buffer[index]

    def __add__(self, other: object, /) -> Self:
        if isinstance(other, str):
            return self.__class__(str(self) + other, self.offset, _check=False)
        if isinstance(other, Line):
            if self.offset != other.offset:
                msg = 'cannot concatenate lines with different offsets'
                raise ValueError(msg)
            return self.__class__(str(self) + str(other), self.offset, _check=False)
        return NotImplemented

    def __mul__(self, other: object, /) -> Self:
        if isinstance(other, int):
            return self.__class__(str(self) * other, self.offset, _check=False)
        return NotImplemented

    def __eq__(self, other: object, /) -> bool:
        other = self.__cast(other)
        if isinstance(other, self.__class__):
            # check offsets before calling str() for efficiency
            return self.offset == other.offset and str(self) == str(other)
        return False

    def __lt__(self, other: object, /) -> bool:
        other = self.__cast(other)
        if isinstance(other, self.__class__):
            # check offsets before calling str() for efficiency
            return self.offset == other.offset and str(self) < str(other)
        return NotImplemented

    def __gt__(self, other: object, /) -> bool:
        other = self.__cast(other)
        if isinstance(other, self.__class__):
            # check offsets before calling str() for efficiency
            return self.offset == other.offset and str(self) > str(other)
        return NotImplemented

    # exposed :class:`str` interface

    def startswith(self, prefix: str, start: int = 0, end: int | None = None, /) -> bool:
        """See :meth:`str.startswith`."""
        return self.buffer.startswith(prefix, start, end)

    def endswith(self, suffix: str, start: int = 0, end: int | None = None, /) -> bool:
        """See :meth:`str.endswith`."""
        return self.buffer.endswith(suffix, start, end)

    def count(self, sub: str, start: int = 0, end: int | None = None, /) -> int:
        """See :meth:`str.count`."""
        return self.buffer.count(sub, start, end)

    def find(self, sub: str, start: int = 0, end: int | None = None, /) -> int:
        """See :meth:`str.find`."""
        return self.buffer.find(sub, start, end)

    def rfind(self, sub: str, start: int = 0, end: int | None = None, /) -> int:
        """See :meth:`str.rfind`."""
        return self.buffer.rfind(sub, start, end)

    def index(self, sub: str, start: int = 0, end: int | None = None, /) -> int:
        """See :meth:`str.index`."""
        return self.buffer.index(sub, start, end)

    def rindex(self, sub: str, start: int = 0, end: int | None = None, /) -> int:
        """See :meth:`str.rindex`."""
        return self.buffer.rindex(sub, start, end)

    def __cast(self, other: object, /) -> Self | object:
        """Try to parse *object* as a :class:`Line`."""
        if isinstance(other, self.__class__):
            return other
        if isinstance(other, str):
            return self.__class__(other, self.offset, _check=False)
        if isinstance(other, (list, tuple)) and len(other) == 2:
            # type checking is handled by the Line constructor
            return self.__class__(other[0], other[1], _check=True)
        return other


@final
class Block(ComparableView[tuple[str, ...]], Sequence[str]):
    """Block found by :meth:`~sphinx.testing.matcher.LineMatcher.find`.

    A block is a sequence of lines comparable to :class:`Line`, generally a
    string (the line content) or a pair ``(line, line_offset)``. In addition,
    a block can be compared to pair ``(block_lines, block_offset)`` where:

    - *block_lines* is a sequence of lines-like objects, and
    - *block_offset* is an integer (matched against :attr:`offset`).

    Whenever a pair ``(line, line_offset)`` or ``(block, block_offset)``
    is needed, it can be any two-element sequence (e.g., tuple or list).

    For instance,::

        assert Block(['a', 'b', 'c'], 2) == ['a', ('b', 3), Line('c', 4)]

    .. note::

       By convention, ``block[i]`` or ``block[i:j]`` returns :class:`str`
       or sequences of :class:`str`. Consider using :meth:`at` to get the
       corresponding :class:`Line` or :class:`Block` values.
    """

    def __init__(
        self, buffer: Iterable[str] = (), offset: int = 0, /, *, _check: bool = True
    ) -> None:
        buffer = tuple(buffer)
        if _check:
            for line in buffer:
                if type(line) is not str:
                    err = f'expecting a native string, got: {line!r}'
                    raise TypeError(err)
        super().__init__(buffer, offset, _check=_check)

    @classmethod
    def view(cls, index: int, buffer: Iterable[str], /) -> Self:
        """Alternative constructor flipping the order of the arguments.

        This is typically useful with :func:`enumerate`, namely this makes::

            from itertools import starmap
            blocks = list(starmap(Block.view, enumerate(src))

        equivalent to::

            blocks = [Block(lines, index) for index, lines in enumerate(src)]
        """
        return cls(buffer, index, _check=True)

    @property
    def length(self) -> int:
        """The number of lines in this block."""
        return len(self)

    @property
    def window(self) -> slice:
        """A slice representing this block in its source.

        If *source* is the original source this block is contained within,
        then ``assert source[block.window] == block`` is always satisfied.

        Example::

            source = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
            block = Block(['4', '5', '6'], 3)
            assert source[block.window] == ['4', '5', '6']
        """
        return slice(self.offset, self.offset + self.length)

    def context(self, delta: int, limit: int) -> tuple[slice, slice]:
        """A slice object indicating a context around this block.

        :param delta: The number of context lines to show.
        :param limit: The number of lines in the source the block belongs to.
        :return: The slices for the 'before' and 'after' lines.

        Example::

           source = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
           block = Block(['4', '5', '6'], 3)
           before, after = block.context(2, 10)
           assert source[before] == ['2', '3']
           assert source[after] == ['7', '8']
        """
        block_stop = self.offset + self.length
        before_slice = slice(max(0, self.offset - delta), min(self.offset, limit))
        after_slice = slice(min(block_stop, limit), min(block_stop + delta, limit))
        return before_slice, after_slice

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.buffer!r}, offset={self.offset})'

    # fmt: off
    @overload
    def at(self, index: int, /) -> Line: ...  # NoQA: E704
    @overload
    def at(self, index: slice, /) -> Self: ...  # NoQA: E704
    # fmt: on
    def at(self, index: int | slice, /) -> Line | Block:  # NoQA: E301
        """Get a :class:`Line` or a contiguous sub-:class:`Block`."""
        if isinstance(index, slice):
            # normalize negative and None slice fields
            start, _, step = index.indices(self.length)
            if step != 1:
                msg = 'only contiguous regions can be extracted'
                raise ValueError(msg)
            return self.__class__(self.buffer[index], self.offset + start, _check=False)

        # normalize negative indices
        start, _, _ = slice(index, -1).indices(self.length)
        return Line(self.buffer[index], self.offset + start, _check=False)

    # fmt: off
    @overload
    def __getitem__(self, index: int, /) -> str: ...  # NoQA: E704
    @overload
    def __getitem__(self, index: slice, /) -> Sequence[str]: ...  # NoQA: E704
    # fmt: on
    def __getitem__(self, index: int | slice, /) -> str | Sequence[str]:  # NoQA: E301
        """Get a line or a contiguous sub-block."""
        return self.at(index).buffer

    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            # more efficient to first check the offsets
            return (self.offset, self.buffer) == (other.offset, other.buffer)

        if isinstance(other, (list, tuple)):
            lines, offset = self.__cast(other)
            # check offsets before computing len(lines) or len(self)
            if (offset, len(lines)) != (self.offset, self.length):
                return False

            expect = starmap(Line.view, enumerate(self, offset))
            # xref py310+: use strict=True
            return all(starmap(Line.__eq__, zip(expect, lines)))
        return False

    def __lt__(self, other: object, /) -> bool:
        # nothing can be a strict subset of the empty block
        if not self:
            return False

        if isinstance(other, self.__class__):
            # more efficient to first check if the indices are valid before checking the lines
            if _can_be_strict_in(self.offset, self.length, other.offset, other.length):
                return self.buffer < other.buffer
            return False

        if isinstance(other, (list, tuple)):
            lines, offset = self.__cast(other)
            if not _can_be_strict_in(self.offset, self.length, offset, len(lines)):
                return False

            expect = list(starmap(Line.view, enumerate(self, self.offset)))
            for candidate in windowed(lines, self.length):
                # xref py310+: use strict=True
                if all(starmap(Line.__eq__, zip(expect, candidate))):
                    return True
            return False

        # other types are not supported for comparison
        return NotImplemented

    def __gt__(self, other: object, /) -> bool:
        if isinstance(other, self.__class__):
            return other < self

        if isinstance(other, (list, tuple)):
            expecting, offset = self.__cast(other)
            batchsize = len(expecting)
            if not _can_be_strict_in(offset, batchsize, self.offset, self.length):
                return False

            for batch in windowed(self, batchsize):
                candidate = starmap(Line.view, enumerate(batch, offset))
                if all(actual == expect for actual, expect in zip(candidate, expecting)):
                    return True
            return False

        # other types are not supported for comparison
        return NotImplemented

    # exposed :class:`tuple` interface

    def index(
        self,
        value: object,
        start: SupportsIndex = 0,
        stop: SupportsIndex = sys.maxsize,
        /,
    ) -> int:
        """See :meth:`tuple.count`."""
        return self.buffer.index(value, start, stop)

    def count(self, value: object, /) -> int:
        """See :meth:`tuple.count`."""
        return self.buffer.count(value)

    def __cast(
        self, other: Sequence[object] | tuple[Sequence[object], int], /
    ) -> tuple[Sequence[object], int]:
        """Try to parse *object* as a pair ``(lines, block offset)``."""
        if len(other) == 2 and isinstance(other[0], Sequence) and isinstance(other[1], int):
            # mypy does not know how to deduce that the lenght is 2
            if isinstance(other, str):
                msg = f'expecting a sequence of lines, got: {other!r}'
                raise ValueError(msg)
            return other[0], other[1]
        return other, self.offset


def _can_be_strict_in(i1: int, l1: int, i2: int, l2: int) -> bool:
    """Check that a block can be strictly contained in another block.

    :param i1: The address (index) of the first block.
    :param l1: The length of the first block.
    :param i2: The address (index) of the second block.
    :param l2: The length of the second block.
    """
    j1, j2 = i1 + l1, i2 + l2
    # Case 1: i1 == i2 and j1 < j2 (block1 is at most block2[:-1])
    # Case 2: i1 > i2 and j1 <= j2 (block1 is at most block2[1:])
    return l1 < l2 and ((i1 >= i2) and (j1 < j2) or (i1 > i2) and (j1 <= j2))
