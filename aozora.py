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
import warnings
from pathlib import Path
from typing import Dict, List, Match

import MeCab
from bs4 import BeautifulSoup as bs
from bs4 import XMLParsedAsHTMLWarning

ruby_pattern = re.compile("<ruby><rb>.*?</rb><rp>.*?</ruby>")
ruby_pattern_old = re.compile("<!R>.*?（.*?）")
ruby = {"start": "<ruby><rb>", "end": "</rb>"}
ruby_old = {"start": "<!R>", "end": "（"}
local_path = "aozorabunko_html/cards/"
dict_path = "60a_kindai-bungo"
out_csv = "t-list_person_all_extended_utf8.csv"
out_path = Path.cwd().joinpath("tokenized")

def init_metadata(source_url:str="https://www.aozora.gr.jp/cards",
                  source_csv:str="list_person_all_extended_utf8.csv",
                  source_path:str="XHTML/HTMLファイルURL") -> Dict[str, List[str]]:
    """Initialize dictionary with metadata from source_csv

    Parameters
    -------
    source_url : str, default="https://www.aozora.gr.jp/cards"
        URL prefix common to Aozora Bunko-hosted HTML files
    source_csv: str, default="list_person_all_extended_utf8.csv"
        Local filename of metadata CSV downloaded from Aozora Bunko
    source_path: str, default="XHTML/HTMLファイルURL"
        Name of metadata CSV column containing HTML file URLs

    Returns
    -------
    metadata : dict
        Key: unique file ID from source_path (source_url prefix stripped)
        Value: list of metadata items in source_csv column order, per file
    """

    metadata = {}

    with (open(source_csv, newline="") as csvin):
        csv_reader = csv.reader(csvin)

        header_row = next(csv_reader)
        html_column = header_row.index(source_path)
        header_row.append("Tokenized Filename")
        metadata["header"] = header_row

        for row in csv_reader:
            # Only store data for files hosted at Aozora URL
            if source_url in row[html_column]:
                file_path = row[html_column].lstrip(source_url)
                if file_path not in metadata:
                    metadata[file_path] = row
    return metadata


def strip_ruby(text: str, ) -> str:
    """Strips ruby annotations and related markup from Aozora HTML files.

    Parameters
    -------
    text : str
        Text including Aozora HTML and ruby markup

    Returns
    -------
    str
        All input text (including ruby-annotated base phrases retained
        inline), stripped of ruby-related markup and annotations

    """

    if ruby["start"] in text:
        return re.sub(ruby_pattern, ruby_replace, text)

    elif ruby_old["start"] in text:
        return re.sub(ruby_pattern_old, ruby_replace_old, text)

    else:
        return text


def ruby_replace(matchobj: Match) -> str:
    """Extracts inline text from ruby pattern matches in standard Aozora files.

    Parameters
    -------
    matchobj : Match
        Individual ruby pattern regex matches from a source text

    Returns
    -------
    str
        Subset of input text, stripped of leading ruby markup and all
        trailing markup or annotations after the base non-ruby phrase

    """

    return matchobj.group(0).lstrip(ruby["start"]).split(ruby["end"])[0]


def ruby_replace_old(matchobj: Match) -> str:
    """Extracts inline text from ruby pattern matches in older Aozora files.

    Parameters
    -------
    matchobj : Match
        Individual ruby pattern regex matches from a source text

    Returns
    -------
    str
        Subset of input text, stripped of leading ruby markup and all
        trailing markup or annotations after the base non-ruby phrase

    """

    return matchobj.group(0).lstrip(ruby_old["start"]).split(ruby_old[
                                                                 "end"])[0]


def to_plain_text(html_text: str) -> str:
    """Removes markup tags to produce a plain-text version of a work.

    Parameters
    -------
    html_text : str
        Aozora HTML file contents

    Returns
    -------
    str

    """

    # Clean up <br /> to avoid excessive line breaks in output
    html_text = html_text.replace("<br />", "")

    # Aozora standard HTML contains exactly ONE div with "main_text" class
    # (used like an ID), so test for 1 result and return markup-stripped text
    soup = bs(html_text, "html5lib").select(".main_text")
    if len(soup) == 1:
        return soup[0].text

    # For older files, return markup-stripped text from <body>
    elif len(soup) == 0:
        soup = bs(html_text, "html5lib").find("body")
        if soup:
            return soup.text

    # Skip processing for files with unexpected structure
    return ""


def main():
    if not (out_path.exists()):
        out_path.mkdir()
    metadata: Dict[str, List[str]] = init_metadata()

    # Create MeCab tagger to reuse for all texts
    tagger = MeCab.Tagger(f"-r {os.devnull!s} -d {dict_path!s} -Owakati")

    # Suppress Beautiful Soup warnings that don"t apply to these files
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

    for filename in metadata:
        # Translate remote Aozora HTML filename to local equivalent
        f = Path.cwd().joinpath(local_path, filename)

        if f.is_file():
            with (open(f, mode="r", encoding="Shift-JIS", errors="ignore") as
                  fin):
                text = fin.read()

            # Remove ruby, markup, standard-format metadata from work text
            text = strip_ruby(text)
            text = to_plain_text(text)

            if text:
                # Tokenize using MeCab parser and rejoin text into one string
                text_lines = text.split("\n")
                parsed_text = "\n".join([tagger.parse(line).strip() for line
                                         in text_lines]).strip()

                # Write results out as .txt file
                out_filename = filename.replace("html", "txt")
                out_filename = out_filename.replace("/", "-")
                out_filename = f"t-{out_filename!s}"
                metadata[filename].append(out_filename)
                with open(out_path.joinpath(out_filename), mode="w",
                          encoding="utf-8") as fout:
                    fout.write(parsed_text)

    # Write out new, work-oriented CSV with added column for tokenized filename
    with open(out_csv, mode="w", encoding="utf-8") as fout:
        w = csv.writer(fout)
        w.writerow(metadata.pop("header"))
        for f in metadata:
            w.writerow(metadata[f])


if __name__ == "__main__":
    main()
