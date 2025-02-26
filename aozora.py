#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Aozora Corpus Builder uses Beautiful Soup and MeCab to create UTF-8,
plain-text, word-tokenized versions of Aozora Bunko HTML files.

This process removes all ruby glosses and markup tags, and separates metadata
from contents in output .txt files (except for very old, non-standard cases).

"""

import os
import csv
import re
from pathlib import Path

from bs4 import BeautifulSoup as bs
import MeCab


RUBY_TAGS = ('rt', 'rp')
RUBY_PATTERN = r"<!R>.*?（.*?）"
RUBY_START = '<!R>'
RUBY_END = '（'
LOCAL_PATH = 'aozorabunko_html/cards/'
SOURCE_URL = 'https://www.aozora.gr.jp'
SOURCE_CSV = 'list_person_all_extended_utf8.csv'
OUT_PATH = Path.cwd().joinpath('tokenized')
OUT_CSV = 't-list_person_all_extended_utf8.csv'

metadata = {}
files = []

# Create MeCab tagger to reuse for all texts
tagger = MeCab.Tagger('-r ' + os.devnull + ' -d 60a_kindai-bungo -Owakati')


def init_metadata():
    """Initialize `metadata` and `files` from SOURCE_CSV

    Key: filename in pattern [digits]-files-[html_filename].html
    Value: list of metadata items in SOURCE_CSV column order

    Filenames are stored in duplicate list for faster processing

    """

    with open(SOURCE_CSV, newline='') as csvin:
        csv_reader = csv.reader(csvin)

        metadata['header'] = next(csv_reader)
        metadata['header'].append('Tokenized Filename')

        for row in csv_reader:
            # Only store data for files hosted at Aozora URL
            if SOURCE_URL in row[50]:
                file_path = '-'.join(row[50].split('/')[4:])
                if file_path not in files:
                    files.append(file_path)
                    metadata[file_path] = row


def ruby_replace(matchobj):
    """Extracts inline text from ruby pattern matches in older Aozora files.

    Parameters
    -------
    matchobj : Match
        Individual ruby pattern regex matches from a source text

    Returns
    -------
    str
        Subset of input text, stripped of leading characters in
        RUBY_START and everything trailing from RUBY_END (inclusive)

    """

    return matchobj.group(0).lstrip(RUBY_START).split(RUBY_END)[0]


def to_plain_text(f):
    """Removes markup tags to produce a plain-text version of a work.

    Parameters
    -------
    f : Path
        Aozora HTML file to open

    Returns
    -------
    str

    """

    with open(f, mode='r', encoding='Shift-JIS', errors='ignore') as fin:
        file_text = fin.read()

    # Remove <br /> to avoid excessive line breaks in output
    file_text = file_text.replace('<br />', '')

    soup = bs(file_text, 'html5lib').select('.main_text')

    # Default case: Remove all markup and ruby with HTML5 parser, return text
    if len(soup) == 1:
        for tag in soup[0].find_all(RUBY_TAGS):
            tag.extract()
        return soup[0].text

    # Known non-standard files with no "main_text" div:
    #   1. Remove non-HTML ruby markup with regular expression match
    #   2. Remove other markup with HTML5 parser, return text in <body>
    elif len(soup) == 0:
        non_ruby = re.sub(RUBY_PATTERN, ruby_replace, file_text)
        soup = bs(non_ruby, 'html5lib').find('body')
        return soup.text

    # Skip processing for other unexpected cases
    else:
        return ''


def main():

    if not (OUT_PATH.exists()):
        OUT_PATH.mkdir()
    init_metadata()

    for f in files:
        # Translate Aozora CSV filename to local file path
        filename = Path.cwd().joinpath(LOCAL_PATH + f.replace('-', '/'))

        if filename.is_file():
            # Get work text only (no ruby, markup, or metadata)
            text = to_plain_text(filename)

            if text:
                # Tokenize using MeCab parser and rejoin text into one string
                text_lines = text.split('\n')
                parsed_text = '\n'.join([tagger.parse(line).strip() for line
                                         in text_lines]).strip()

                # Write results out as .txt file
                out_filename = 't-' + str(filename).replace('html', 'txt')
                metadata[filename].append(out_filename)
                with open(OUT_PATH.joinpath(out_filename), mode='w',
                          encoding='utf-8') as fout:
                    fout.write(parsed_text)

    # Write out new, work-oriented CSV with added column for tokenized filename
    with open(OUT_CSV, mode='w', encoding='utf-8') as fout:
        w = csv.writer(fout)
        w.writerow(metadata['header'])
        for f in files:
            w.writerow(metadata[f])


main()
