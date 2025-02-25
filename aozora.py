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
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup as bs
import MeCab


RUBY_TAGS = ('rt', 'rp')
LOCAL_PATH = 'aozorabunko_html/cards/'
SOURCE_URL = 'https://www.aozora.gr.jp'
SOURCE_CSV = 'list_person_all_extended_utf8.csv'
OUT_PATH = Path.cwd().joinpath('tokenized')
OUT_CSV = 't-list_person_all_extended_utf8.csv'

result_metadata = {}
files = []

# Create MeCab tagger to reuse for all texts
tagger = MeCab.Tagger('-r ' + os.devnull + ' -d 60a_kindai-bungo -Owakati')


def init_metadata():
    """Initialize result_metadata{} and files[] from SOURCE_CSV

    Key: filename in format "[digits]-files-[html_filename].html"
    Value: list of metadata items in SOURCE_CSV column order

    Filenames are stored in duplicate list for faster processing

    """

    with open(SOURCE_CSV, newline='') as csvin:
        csv_reader = csv.reader(csvin)

        result_metadata['header'] = next(csv_reader)
        result_metadata['header'].append('Tokenized Filename')
        result_metadata['header'].append('Time Processed (UTC)')

        for row in csv_reader:
            # Only store data for files hosted at Aozora URL
            if SOURCE_URL in row[50]:
                file_path = '-'.join(row[50].split('/')[4:])
                if file_path not in files:
                    files.append(file_path)
                    result_metadata[file_path] = row


def ruby_replace(matchobj):
    """Uses ruby pattern to extract and return inline text only.

    Parameters
    -------
    matchobj : Match

    Returns
    -------
    str

    """

    return matchobj.string[4:].split('（')[0]


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
    file_text = file_text.replace("<br />", "")

    soup = bs(file_text, "html5lib").select(".main_text")

    # Default case: Remove all markup and ruby with HTML5 parser, return text
    if len(soup) == 1:
        for tag in soup[0].find_all(RUBY_TAGS):
            tag.extract()
        return soup[0].text

    # Known non-standard files with no "main_text" div:
    #   1. Remove non-HTML ruby markup with regular expression match
    #   2. Remove other markup with HTML5 parser, return text in <body>
    elif len(soup) == 0:
        non_ruby = re.sub(r"<!R>.*?（.*?）", ruby_replace, file_text)
        soup = bs(non_ruby, "html5lib").find("body")
        return soup.text

    # Skip processing for other unexpected cases
    else:
        return ""


def main():

    if not (OUT_PATH.exists()):
        OUT_PATH.mkdir()
    init_metadata()

    for filename in files:
        # Translate Aozora CSV filename to local file path
        in_path = Path.cwd().joinpath(LOCAL_PATH + filename.replace('-', '/'))

        if in_path.is_file():
            # Get work text only (no ruby, markup, or metadata)
            text = to_plain_text(in_path)

            if text:
                # Tokenize using MeCab parser and rejoin text into one string
                text_lines = text.split('\n')
                parsed_lines = [tagger.parse(line).strip() for line in
                                text_lines]
                parsed_full = '\n'.join(parsed_lines).strip()

                # Write results out as .txt file
                out_filename = 't-' + filename[:-5] + '.txt'
                with open(OUT_PATH.joinpath(out_filename), mode='w',
                          encoding='utf-8') as fout:
                    fout.write(parsed_full)

                # Add tokenized filename to respective metadata row
                result_metadata[filename].append(out_filename)
                result_metadata[filename].append(str(datetime.now(
                    timezone.utc)))

    # Save new CSV with all original Aozora metadata, adding columns
    # for new tokenized filename and processing timestamp
    with open(OUT_CSV, mode='w', encoding='utf-8') as fout:
        w = csv.writer(fout)
        w.writerow(result_metadata['header'])
        for filename in files:
            w.writerow(result_metadata[filename])


main()
