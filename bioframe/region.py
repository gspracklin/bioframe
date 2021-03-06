from __future__ import absolute_import, division, print_function
import six
import re

import numpy as np
import pandas as pd


def parse_humanized(s):
    _NUMERIC_RE = re.compile('([0-9,.]+)')
    _, value, unit = _NUMERIC_RE.split(s.replace(',', ''))
    if not len(unit):
        return int(value)

    value = float(value)
    unit = unit.upper().strip()
    if unit in ('K', 'KB'):
        value *= 1000
    elif unit in ('M', 'MB'):
        value *= 1000000
    elif unit in ('G', 'GB'):
        value *= 1000000000
    else:
        raise ValueError("Unknown unit '{}'".format(unit))
    return int(value)


def parse_region_string(s):
    """
    Parse a UCSC-style genomic region string into a triple.

    Parameters
    ----------
    s : str
        UCSC-style string, e.g. "chr5:10,100,000-30,000,000". Ensembl and FASTA
        style sequence names are allowed. End coordinate must be greater than or
        equal to start.

    Returns
    -------
    (str, int or None, int or None)

    """
    def _tokenize(s):
        token_spec = [
            ('HYPHEN', r'-'),
            ('COORD',  r'[0-9,]+(\.[0-9]*)?(?:[a-z]+)?'),
            ('OTHER',  r'.+')
        ]
        tok_regex = r'\s*' + r'|\s*'.join(
            r'(?P<%s>%s)' % pair for pair in token_spec)
        tok_regex = re.compile(tok_regex, re.IGNORECASE)
        for match in tok_regex.finditer(s):
            typ = match.lastgroup
            yield typ, match.group(typ)


    def _check_token(typ, token, expected):
        if typ is None:
            raise ValueError('Expected {} token missing'.format(
                ' or '.join(expected)))
        else:
            if typ not in expected:
                raise ValueError('Unexpected token "{}"'.format(token))


    def _expect(tokens):
        typ, token = next(tokens, (None, None))
        _check_token(typ, token, ['COORD'])
        start = parse_humanized(token)

        typ, token = next(tokens, (None, None))
        _check_token(typ, token, ['HYPHEN'])

        typ, token = next(tokens, (None, None))
        if typ is None:
            return start, None

        _check_token(typ, token, ['COORD'])
        end = parse_humanized(token)
        if end < start:
            raise ValueError('End coordinate less than start')

        return start, end

    parts = s.split(':')
    chrom = parts[0].strip()
    if not len(chrom):
        raise ValueError("Chromosome name cannot be empty")
    if len(parts) < 2:
        return (chrom, None, None)
    start, end = _expect(_tokenize(parts[1]))
    return (chrom, start, end)


def parse_region(reg, chromsizes=None):
    """
    Genomic regions are represented as half-open intervals (0-based starts,
    1-based ends) along the length coordinate of a contig/scaffold/chromosome.

    Parameters
    ----------
    reg : str or tuple
        UCSC-style genomic region string, or
        Triple (chrom, start, end), where ``start`` or ``end`` may be ``None``.
    chromsizes : mapping, optional
        Lookup table of scaffold lengths to check against ``chrom`` and the
        ``end`` coordinate. Required if ``end`` is not supplied.

    Returns
    -------
    A well-formed genomic region triple (str, int, int)

    """
    if isinstance(reg, six.string_types):
        chrom, start, end = parse_region_string(reg)
    else:
        chrom, start, end = reg
        start = int(start) if start is not None else start
        end = int(end) if end is not None else end

    try:
        clen = chromsizes[chrom] if chromsizes is not None else None
    except KeyError:
        raise ValueError("Unknown sequence label: {}".format(chrom))

    start = 0 if start is None else start
    if end is None:
        end = clen # if clen is None, end is None too!

    if (end is not None) and (end < start):
        raise ValueError("End cannot be less than start")

    if start < 0 or (clen is not None and end > clen):
        raise ValueError(
            "Genomic region out of bounds: [{}, {})".format(start, end))

    return chrom, start, end
