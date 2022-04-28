"""Porter Stemming Algorithm

This is the Porter stemming algorithm, ported to Python from the
version coded up in ANSI C by the author. It may be be regarded
as canonical, in that it follows the algorithm presented in

Porter, 1980, An algorithm for suffix stripping, Program, Vol. 14,
no. 3, pp 130-137,

only differing from it at the points made --DEPARTURE-- below.

See also https://tartarus.org/martin/PorterStemmer/

The algorithm as described in the paper could be exactly replicated
by adjusting the points of DEPARTURE, but this is barely necessary,
because (a) the points of DEPARTURE are definitely improvements, and
(b) no encoding of the Porter stemmer I have seen is anything like
as exact as this version, even with the points of DEPARTURE!

Release 1: January 2001

:author: Vivake Gupta <v@nano.com>.
:license: Public Domain ("can be used free of charge for any purpose").
"""


class PorterStemmer:

    def __init__(self) -> None:
        """The main part of the stemming algorithm starts here.

        Note that only lower case sequences are stemmed. Forcing to lower case
        should be done before stem(...) is called.
        """

        self.b: str = ""     # buffer for word to be stemmed
        self.j: int = 0      # j is a general offset into the string

    @staticmethod
    def is_consonant(char: str, i: int, word: str) -> bool:
        """is_consonant(char, i, word) is True <=> char is a consonant."""
        if char in {'a', 'e', 'i', 'o', 'u'}:
            return False
        if char == 'y':
            if i == 0:
                return True
            return not PorterStemmer.is_consonant(word[i - 1], i - 1, word)
        return True

    @staticmethod
    def measure_consonant_sequences(word: str, end: int) -> int:
        """Measures the number of consonant sequences in word[:end].
        if c is a consonant sequence and v a vowel sequence, and <..>
        indicates arbitrary presence,

           <c><v>       gives 0
           <c>vc<v>     gives 1
           <c>vcvc<v>   gives 2
           <c>vcvcvc<v> gives 3
           ....
        """
        i = 0
        while (i <= end) and PorterStemmer.is_consonant(word[i], i, word):
            i += 1
        n = 0
        while True:
            while (i <= end) and not PorterStemmer.is_consonant(word[i], i, word):
                i += 1

            if i > end:
                return n
            n += 1

            while (i <= end) and PorterStemmer.is_consonant(word[i], i, word):
                i += 1

    @staticmethod
    def vowel_in_stem(word: str, end: int) -> bool:
        """vowel_in_stem() is True <=> word[:end] contains a vowel"""
        for i in range(end + 1):
            if not PorterStemmer.is_consonant(word[i], i, word):
                return True
        return False

    @staticmethod
    def double_consonant(word: str, end: int) -> bool:
        """True <=> word[end-1:end+1] contains a double consonant."""
        if end < 1:
            return False
        if word[end] != word[end - 1]:
            return False
        return PorterStemmer.is_consonant(word[end], end, word)

    @staticmethod
    def consonant_vowel_consonant(word: str, end: int) -> bool:
        """consonant_vowel_consonant(word, end) is TRUE <=> i-2,i-1,i has the form
             consonant - vowel - consonant
        and also if the second c is not w,x or y. this is used when trying to
        restore an e at the end of a short  e.g.

           cav(e), lov(e), hop(e), crim(e), but
           snow, box, tray.
        """
        return (
            end >= 2
            and PorterStemmer.is_consonant(word[end], end, word)
            and not PorterStemmer.is_consonant(word[end-1], end-1, word)
            and PorterStemmer.is_consonant(word[end-2], end-2, word)
            and word[end] not in {'w', 'x', 'y'}
        )

    def ends(self, s: str) -> bool:
        """True <=> b[:k+1] ends with the string s."""
        if not self.b[:len(self.b) - 1+1].endswith(s):
            return False
        self.j = len(self.b) - 1 - len(s)
        return True

    def set_to(self, s: str, start: int) -> None:
        """set_to(s) sets (j+1),...k to the characters in the string s,
        readjusting k."""
        b = [*self.b]
        b[start + 1:start + 1 + len(s)] = s
        self.b = ''.join(b[:start + 1 + len(s)])

    def r(self, s: str) -> None:
        """r(s) is used further down."""
        _j = self.j
        if self.measure_consonant_sequences(self.b, _j) > 0:
            self.set_to(s, _j)

    def step1ab(self) -> None:
        """step1ab() gets rid of plurals and -ed or -ing. e.g.

           caresses  ->  caress
           ponies    ->  poni
           ties      ->  ti
           caress    ->  caress
           cats      ->  cat

           feed      ->  feed
           agreed    ->  agree
           disabled  ->  disable

           matting   ->  mat
           mating    ->  mate
           meeting   ->  meet
           milling   ->  mill
           messing   ->  mess

           meetings  ->  meet
        """
        if self.b[len(self.b) - 1] == 's':
            if self.ends("sses"):
                self.b = self.b[:-2]
            elif self.ends("ies"):
                self.set_to("i", self.j)
            elif self.b[len(self.b) - 1 - 1] != 's':
                self.b = self.b[:-1]
        if self.ends("eed"):
            if self.measure_consonant_sequences(self.b, self.j) > 0:
                self.b = self.b[:-1]
        elif (self.ends("ed") or self.ends("ing")) and self.vowel_in_stem(self.b, self.j):
            self.b = self.b[:self.j + 1]
            if self.ends("at"):
                self.set_to("ate", self.j)
            elif self.ends("bl"):
                self.set_to("ble", self.j)
            elif self.ends("iz"):
                self.set_to("ize", self.j)
            elif self.double_consonant(self.b, len(self.b) - 1):
                if self.b[len(self.b) - 1 - 1] not in {'l', 's', 'z'}:
                    self.b = self.b[:-1]
            elif self.measure_consonant_sequences(self.b, self.j) == 1 and self.consonant_vowel_consonant(self.b, len(self.b) - 1):
                self.set_to("e", self.j)

    def step1c(self) -> None:
        """step1c() turns terminal y to i when there is another vowel in
        the stem."""
        if self.ends("y") and self.vowel_in_stem(self.b, self.j):
            self.b = self.b[:len(self.b) - 1] + 'i' + self.b[len(self.b) - 1 + 1:]

    def step2(self) -> None:
        """step2() maps double suffices to single ones.
        so -ization ( = -ize plus -ation) maps to -ize etc. note that the
        string before the suffix must give measure_consonant_sequences(self.b, self.j) > 0.
        """
        char = self.b[len(self.b) - 1 - 1]
        if char == 'a':
            if self.ends("ational"):
                self.r("ate")
            elif self.ends("tional"):
                self.r("tion")
        elif char == 'c':
            if self.ends("enci"):
                self.r("ence")
            elif self.ends("anci"):
                self.r("ance")
        elif char == 'e':
            if self.ends("izer"):
                self.r("ize")
        elif char == 'l':
            if self.ends("bli"):
                self.r("ble")  # --DEPARTURE--
            # To match the published algorithm, replace this phrase with
            #   if self.ends("abli"):      self.r("able")
            elif self.ends("alli"):
                self.r("al")
            elif self.ends("entli"):
                self.r("ent")
            elif self.ends("eli"):
                self.r("e")
            elif self.ends("ousli"):
                self.r("ous")
        elif char == 'o':
            if self.ends("ization"):
                self.r("ize")
            elif self.ends("ation"):
                self.r("ate")
            elif self.ends("ator"):
                self.r("ate")
        elif char == 's':
            if self.ends("alism"):
                self.r("al")
            elif self.ends("iveness"):
                self.r("ive")
            elif self.ends("fulness"):
                self.r("ful")
            elif self.ends("ousness"):
                self.r("ous")
        elif char == 't':
            if self.ends("aliti"):
                self.r("al")
            elif self.ends("iviti"):
                self.r("ive")
            elif self.ends("biliti"):
                self.r("ble")
        elif char == 'g':  # --DEPARTURE--
            if self.ends("logi"):
                self.r("log")
        # To match the published algorithm, delete this phrase

    def step3(self) -> None:
        """step3() dels with -ic-, -full, -ness etc. similar strategy
        to step2."""
        char = self.b[len(self.b) - 1]
        if char == 'e':
            if self.ends("icate"):
                self.r("ic")
            elif self.ends("ative"):
                self.r("")
            elif self.ends("alize"):
                self.r("al")
        elif char == 'i':
            if self.ends("iciti"):
                self.r("ic")
        elif char == 'l':
            if self.ends("ical"):
                self.r("ic")
            elif self.ends("ful"):
                self.r("")
        elif char == 's':
            if self.ends("ness"):
                self.r("")

    def step4(self) -> None:
        """step4() takes off -ant, -ence etc., in context <c>vcvc<v>."""
        char = self.b[len(self.b) - 1 - 1]
        if char == 'a':
            if self.ends("al"):
                pass
            else:
                return
        elif char == 'c':
            if self.ends("ance"):
                pass
            elif self.ends("ence"):
                pass
            else:
                return
        elif char == 'e':
            if self.ends("er"):
                pass
            else:
                return
        elif char == 'i':
            if self.ends("ic"):
                pass
            else:
                return
        elif char == 'l':
            if self.ends("able"):
                pass
            elif self.ends("ible"):
                pass
            else:
                return
        elif char == 'n':
            if self.ends("ant"):
                pass
            elif self.ends("ement"):
                pass
            elif self.ends("ment"):
                pass
            elif self.ends("ent"):
                pass
            else:
                return
        elif char == 'o':
            if self.ends("ion") and (self.b[self.j] in 'st'):
                pass
            elif self.ends("ou"):
                pass
            # takes care of -ous
            else:
                return
        elif char == 's':
            if self.ends("ism"):
                pass
            else:
                return
        elif char == 't':
            if self.ends("ate"):
                pass
            elif self.ends("iti"):
                pass
            else:
                return
        elif char == 'u':
            if self.ends("ous"):
                pass
            else:
                return
        elif char == 'v':
            if self.ends("ive"):
                pass
            else:
                return
        elif char == 'z':
            if self.ends("ize"):
                pass
            else:
                return
        else:
            return
        if self.measure_consonant_sequences(self.b, self.j) > 1:
            self.b = self.b[:self.j + 1]

    def step5(self) -> None:
        """step5() removes a final -e if measure_consonant_sequences(self.b, self.j) > 1, and changes -ll to -l if
        measure_consonant_sequences(self.b, self.j) > 1.
        """
        if self.b[len(self.b) - 1] == 'e':
            a = self.measure_consonant_sequences(self.b, len(self.b) - 1)
            if a > 1 or (a == 1 and not self.consonant_vowel_consonant(self.b, len(self.b) - 1 - 1)):
                self.b = self.b[:-1]
        if self.b[len(self.b) - 1] == 'l' and self.double_consonant(self.b, len(self.b) - 1) and self.measure_consonant_sequences(self.b, len(self.b) - 1) > 1:
            self.b = self.b[:-1]

    def stem(self, word: str) -> str:
        """The string to be stemmed is ``word``.
        The stemmer returns the stemmed string.
        """

        # With this line, strings of length 1 or 2 don't go through the
        # stemming process, although no mention is made of this in the
        # published algorithm. Remove the line to match the published
        # algorithm.
        if len(word) <= 2:
            return word  # --DEPARTURE--

        # copy the parameters into statics
        self.b = word

        self.step1ab()
        self.step1c()
        self.step2()
        self.step3()
        self.step4()
        self.step5()
        return self.b[:len(self.b) - 1 + 1]


if __name__ == '__main__':
    stemmer = PorterStemmer()
    stemmer.stem("agreed")
