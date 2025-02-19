#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Aozora Corpus Builder (aozora.py)
This script converts Aozora Bunko HTML files to UTF-8 plain-text,
word-tokenized versions using MeCab and Beautiful Soup.
Author: Molly Des Jardin
License: MIT
"""

from datetime import datetime, timezone
from bs4 import BeautifulSoup as bs
from pathlib import Path
import os
import csv
import re
import MeCab

ruby_tags = ('rt', 'rp')
local_path = 'aozorabunko_html/cards/'
source_url = 'https://www.aozora.gr.jp'
out_path = Path.cwd().joinpath('tokenized')
source_csv = 'list_person_all_extended_utf8.csv'

# Create the tagger to reuse for all texts
# (explicitly ignore config with -r /dev/null, specify dictionary with -d)
tagger = MeCab.Tagger('-r ' + os.devnull + ' -d 60a_kindai-bungo -Owakati')

# Dictionary of metadata, one list per row, filled in init_metadata()
# Keys are filenames in format "[digits]-files-[html_filename].html"
# The filenames are also stored in list files[] for faster processing
result_metadata = {}
files = []


def init_metadata():
    """
    Initializes result_metadata{} with header from Aozora CSV.
    From Aozora CSV, reads HTML file URLs and saves metadata for each file
    as an in-order list of fields corresponding to the header in
    result_metadata (using local path as key). Filenames are stored in files[].
    """

    with open(source_csv, newline='') as csvin:
        csv_reader = csv.reader(csvin)

        result_metadata['header'] = next(csv_reader)
        result_metadata['header'].append('Tokenized Filename')
        result_metadata['header'].append('Time Processed (UTC)')

        for row in csv_reader:
            # Only store data for files hosted at Aozora URL
            if source_url in row[50]:
                file_path = '-'.join(row[50].split('/')[4:])
                if file_path not in files:
                    files.append(file_path)
                    result_metadata[file_path] = row


def ruby_replace(matchobj):
    """
    Find ruby annotation pattern for non-standard files, using matchobj
    regular expression.
    Return the first (0th) string extracted from the ruby pattern, which
    is the inline text (not gloss or punctuation).
    """

    return matchobj.string[4:].split('（')[0]


def to_plain_text(f):
    """
    Removes ruby (annotation and gloss) and HTML markup tags.
    If successful, returns plain text string of work content.
    If failure, returns empty string.
    """

    with open(f, mode='r', encoding='Shift-JIS', errors='ignore') as fin:
        file_text = fin.read()

    # Delete excess <br /> present in older files that don't have <p> tags,
    # to prevent output from having excessive line-break whitespace.
    file_text = file_text.replace("<br />", "")

    soup = bs(file_text, "html5lib").select(".main_text")

    # Default case, use Beautiful Soup parser to remove ruby, return text
    if len(soup) == 1:
        for tag in soup[0].find_all(ruby_tags):
            tag.extract()
        return soup[0].text

    # If no "main_text" div found:
    #   - Use regex match to retain glossed word without ruby or punctuation
    #   - Use Beautiful Soup parser to return text within <body> tag
    elif len(soup) == 0:
        non_ruby = re.sub(r"<!R>.*?（.*?）", ruby_replace, file_text)
        soup = bs(non_ruby, "html5lib").find("body")
        return soup.text

    # Skip processing for other unexpected cases
    else:
        return ""


def main():

    if not (out_path.exists()):
        out_path.mkdir()
    init_metadata()

    for filename in files:
        in_path = Path.cwd().joinpath(local_path + filename.replace('-', '/'))

        # 1. Remove ruby
        # 2. Get only "main" work text (no HTML tags or metadata)
        if in_path.is_file():
            text = to_plain_text(in_path)

        # 3. Tokenize using MeCab & save output txt file
            if text:
                text_lines = text.split('\n')
                parsed_lines = [tagger.parse(line).strip() for line in
                                text_lines]
                parsed_full = '\n'.join(parsed_lines).strip()
                out_filename = 't-' + filename[:-5] + '.txt'
                with open(out_path.joinpath(out_filename), mode='w',
                          encoding='utf-8') as fout:
                    fout.write(parsed_full)
                result_metadata[filename].append(out_filename)
                result_metadata[filename].append(str(datetime.now(
                    timezone.utc)))

    # Save CSV with all original Aozora metadata per each file (row), plus
    # output filename and processing timestamp as extra columns
    out_csv = Path.cwd().joinpath('t-list_person_all_extended_utf8.csv')
    with open(out_csv, mode='w', encoding='utf-8') as fout:
        w = csv.writer(fout)
        w.writerow(result_metadata['header'])
        for filename in files:
            w.writerow(result_metadata[filename])


main()
