#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright Molly Des Jardin
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
 
from datetime import datetime, timezone
from bs4 import BeautifulSoup as bs
from pathlib import Path
import os
import csv
import re
import MeCab

rubytags = ['rt', 'rp']
localpath = 'aozorabunko_html/cards/'
sourceurl = 'https://www.aozora.gr.jp'
outpath = Path.cwd().joinpath('tokenized')
sourcecsv = 'list_person_all_extended_utf8.csv'

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
    as an in-order list of fields corresponding to the header in result_metadata (using local path as key). Filenames are stored in files[].
    """

    with open (sourcecsv, newline='') as csvin:
        csvreader = csv.reader(csvin)

        result_metadata['header'] = next(csvreader)
        result_metadata['header'].append('Tokenized Filename')
        result_metadata['header'].append('Time Processed (UTC)')

        for row in csvreader:
            if sourceurl in row[50]:
            # Only store data for files hosted at Aozora URL
                filepath = '-'.join(row[50].split('/')[4:])
                if filepath not in files:
                    files.append(filepath)
                    result_metadata[filepath] = row
                    

def ruby_replace(matchobj):
    """
    Find ruby annotation pattern for non-standard files, using matchobj regular expression.
    Return the first (0th) string extracted from the ruby pattern, which
    is the inline text (not gloss or punctuation).
    """

    return matchobj.string[4:].split('（')[0]


def plaintext(f):
    """
    Removes ruby (annotation and gloss) and HTML markup tags.
    If successful, returns plain text string of work content.
    If failure, returns empty string.
    """

    with open(f, mode='r', encoding='Shift-JIS', errors='ignore') as fin:
        filetext = fin.read()
        
    # Delete excess <br /> present in older files that don't have <p> tags,
    # to prevent output from having excessive line-break whitespace.
    filetext = filetext.replace("<br />", "")

    soup = bs(filetext, "html5lib").select(".main_text")

    # Default case, use Beautiful Soup parser to remove ruby, return text
    if len(soup) == 1:
        for tag in soup[0].find_all(rubytags):
            tag.extract()
        return soup[0].text

    # If no "main_text" div found:
    #   - Use regex match to retain glossed word without ruby or punctuation
    #   - Use Beautiful Soup parser to return text within <body> tag
    elif len(soup) == 0:
        nonruby = re.sub(r"<!R>.*?（.*?）", ruby_replace, filetext)
        soup = bs(nonruby, "html5lib").find("body")
        return soup.text

    # Skip processing for other unexpected cases
    else:
        return ""


def main():

    if (not(outpath.exists())):
        outpath.mkdir()    
    init_metadata()

    for filename in files:
        inpath = Path.cwd().joinpath(localpath + filename.replace('-', '/'))

        # 1. Remove ruby
        # 2. Get only "main" work text (no HTML tags or metadata)
        if inpath.is_file():
            text = plaintext(inpath)

        # 3. Tokenize using MeCab & save output txt file
            if text:
                textlines = text.split('\n')
                parsedlines = [tagger.parse(line).strip() for line in textlines]
                parsed = '\n'.join(parsedlines).strip()
                outfilename = 't-' + filename[:-5] + '.txt'
                with open(outpath.joinpath(outfilename), mode='w', encoding='utf-8') as fout:
                    fout.write(parsed)
                result_metadata[filename].append(outfilename)
                result_metadata[filename].append(str(datetime.now(timezone.utc)))

    # Save CSV with all original Aozora metadata per each file (row), plus
    # output filename and processing timestamp as extra columns
    outcsv = Path.cwd().joinpath('t-list_person_all_extended_utf8.csv')
    with open(outcsv, mode='w', encoding='utf-8') as fout:
        w = csv.writer(fout)
        w.writerow(result_metadata['header'])
        for filename in files:
            w.writerow(result_metadata[filename])

main()
