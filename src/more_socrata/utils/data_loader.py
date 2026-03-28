from __future__ import annotations

from .log_helper import BasicLogger, logging
from .response import Response

import os
import re
import json
import pandas as pd
import io
import urllib.parse as urlparser
from typing import Union, Optional, List

class FilePathError(Exception):
    pass

class UnsupportedExtension(Exception):
    pass


class Dataset:
    """
    provide doc_url for an url or the file_path to a file
    """
    def __init__(self, debug:bool=False, **kwargs):
        """Initializes the object with optional parameters.

        Args:
            **kwargs: A dictionary of keyword arguments.  The following keys are supported:
                - doc_url (str): The URL of the documentation.
                - file_path (str): The path to a file.

        """
        self.doc_url = None
        self.file_path = None
        if "doc_url" in kwargs:
            self.doc_url = kwargs.get("doc_url")
        elif "file_path" in kwargs:
            self.file_path = kwargs.get("file_path")
        else:
            raise ValueError("No doc_url or file_path provided")
        self.kwargs = {k:v for k,v in kwargs.items() if k not in ["doc_url", "file_path"]}
        self._supported_extensions = ["csv", "ods", "xlsx", "xls", "json", "pdf",
                                     "text/csv", "geojson", "txt"]
        self._bl = BasicLogger(verbose=False, 
                               log_directory=None, 
                               logger_name="DATA_LOADER", 
                               log_level = logging.DEBUG if debug else logging.INFO)
        
        self._bl.debug(f"doc_url: {self.doc_url}")
        self._bl.debug(f"file_path: {self.file_path}")
        self._bl.debug(f"kwargs: {self.kwargs}")
    
    def _response(self, **kwargs):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/css,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        kwargs.update(self.kwargs)
        url = kwargs.pop("url", None) or self.doc_url
        if url:
            return Response(url, headers=headers, **kwargs).assert_response()
        else:
            raise ValueError("No URL available to make a request")
    
    def _guess_extension(self):
    
        if self.doc_url:
            response = self._response()
            return response.headers.get("Content-Type")
        
    @property
    def _extension(self):
        if hasattr(self, '__extension_override') and self.__extension_override:
            return self.__extension_override
        extension = os.path.splitext(self.doc_url or self.file_path)[1]
        if extension:
            return extension
        else:

            return None

    @_extension.setter
    def _extension(self, value):
        self.__extension_override = value

    @property
    def _github_doc_url(self):
        if self.doc_url:
            if "github" in self.doc_url:
                return re.sub("blob", "raw", self.doc_url)
    
    @property
    def _assert_file_path(self):
        if self.file_path:
            if not os.path.exists(self.file_path):
                raise FileNotFoundError("File path does not exist")

    def _check_extension(self, extension:str):
        extension = extension.lower()
        if not any(extension.endswith(x) for x in self._supported_extensions) and \
            not any(x in re.sub("\\.", "", extension) for x in self._supported_extensions):
            raise UnsupportedExtension(f"Extension: {extension} is not supported")
        
    
    def _try_loading_from_github(self):
        if self.doc_url and "github" in self.doc_url:
            path = urlparser.urlsplit(self.doc_url).path
            doc_url = re.sub("blob", "refs/heads", urlparser.urljoin("https://raw.githubusercontent.com", path))
            #self._bl.info(doc_url)
            return self._response(url=doc_url)
        
    @property    
    def _load_csv(self):
        import csv

        if self.doc_url:
            if "github" in self.doc_url:
            #    url = self._github_doc_url
                response = self._try_loading_from_github()
            else:
                url= self.doc_url
                response = self._response(url=url)

            if not self._extension:
                self._extension = response.headers.get("Content-Type")

            with io.StringIO(response.text) as f:
                dat = csv.DictReader(f)
                col_names = dat.fieldnames
                if col_names:
                    self._bl.debug(f"columns: {col_names}")
                    self._bl.debug("Converting the response into json format")
                content = [{col.replace(" ", "_").lower() : row[col] for col in col_names} for row in dat]
                non_empty_content = [x for x in content if x]
            if not non_empty_content:
                if "github" in self.doc_url:
                    path = urlparser.urlsplit(self.doc_url).path
                    doc_url = re.sub("blob", "refs/heads", urlparser.urljoin("https://raw.githubusercontent.com", path))
                else:
                    doc_url=self.doc_url
                df=pd.read_csv(doc_url)
                df.columns = [re.sub(" ", "_", str(x).lower()) for x in df.columns]
                content = json.loads(df.to_json(orient="records"))

        
        elif self.file_path:
            self._assert_file_path

            with open(self.file_path, "r") as f:
                dat = csv.DictReader(f)
                col_names = dat.fieldnames
                self._bl.debug(f"columns: {col_names}")
                self._bl.debug("Converting the response into json format")
                content = [{col.replace(" ", "_").lower() : row[col] for col in col_names} for row in dat]
        
        
        return content
    
    @property
    def _load_ods(self):
        if self.doc_url:
            response = self._response(url=self.doc_url)
            content = io.BytesIO(response.content)
        elif self.file_path:
            content = self.file_path
        
        xls = pd.ExcelFile(content)
        self._bl.debug(f"Sheets in this file: {xls.sheet_names}")
        out = {}
        for sheet in xls.sheet_names:
            out[sheet] = pd.read_excel(xls, sheet, engine="odf")
        
        return out
    @property
    def _load_excel(self):
        if self.doc_url:
            content = io.BytesIO(self._response().content)
        elif self.file_path:
            content = self.file_path
        
        xls = pd.ExcelFile(content)
        out = {}
        self._bl.debug(f"Sheets in this file: {xls.sheet_names}")
        for sheet in xls.sheet_names:
            out[sheet] = pd.read_excel(xls, sheet)
        return out
    @property
    def _load_json(self):
        if self.doc_url:
            try:
                responseDict = json.loads(self._response().content)
            except:
                try:
                    path = urlparser.urlsplit(self.doc_url).path
                    if "github" in self.doc_url:
                        doc_url = re.sub("blob", "refs/heads", urlparser.urljoin("https://raw.githubusercontent.com", path))
                        self._bl.debug(f"{doc_url=}")
                        responseDict = json.loads(self._response(url=doc_url).content)
                except Exception as e:
                    self._bl.exception(f"Failed to load data : \n\t{e}")
                    pass
        elif self.file_path:
            self._assert_file_path
            with open(self.file_path, "r") as f:
                responseDict = json.load(f)
        
        return responseDict
    
    @property
    def _load_pdf(self):
        import pdfplumber
        if self.doc_url:
            try:
                content = io.BytesIO(self._response().content)
                return pdfplumber.open(content)
            except Exception as e:
                self._bl.exception(f"Error obtaining pdf from url\n\t{e}")
        
        elif self.file_path:
            self._assert_file_path
            try:
                return pdfplumber.open(self.file_path)
            except Exception as e:
                self._bl.exception(f"Failed to load pdf from filepath\n\t{e}")
    
    @property
    def _load_geojson(self):
        import geopandas as gpd
        if self.doc_url:
            try:
                return gpd.read_file(self.doc_url)
            except Exception as e:
                self._bl.exception("Failed to load geojson from url\n\t{e}")
        elif self.file_path:
            try:
                return gpd.read_file(self.file_path)
            except Exception as e:
                self._bl.exception("Failed to load geojson from file\n\t{e}")
    
    @property
    def _load_text(self):
        if self.doc_url:
            try:
                return self._response().text
            except Exception as e:
                self._bl.exception("Failed to load text from url\n\t{e}")
        elif self.file_path:
            try:
                with open(self.file_path, "r") as f:
                    return f.read()
            except Exception as e:
                self._bl.exception("Failed to load text from file\n\t{e}")

    @property
    def _load_for_extension(self):
        extension = self._extension
        if extension:
            extension = extension.lower()
            self._check_extension(extension)
            if extension.endswith("csv") or "csv" in extension:
                try:
                    return self._load_csv
                except Exception as e:
                    self._bl.exception(f"Failed to load from csv: {str(e)}")
            elif extension.endswith("ods") or "ods" in extension:
                try:
                    return self._load_ods
                except Exception as e:
                    self._bl.exception(f"Failed to load from ODS: {str(e)}")
            elif extension.endswith("xlsx") or extension.endswith("xls") or \
                "xlsx" in extension or "xls" in extension:
                try:
                    return self._load_excel
                except Exception as e:
                    self._bl.exception(f"Failed to load from excel: {str(e)}")
            elif extension.endswith("json") or "json" in extension:
                try:
                    return self._load_json
                except Exception as e:
                    self._bl.exception(f"Failed to load from json: {str(e)}")
            elif extension.endswith("pdf") or "pdf" in extension:
                try:
                    return self._load_pdf
                except Exception as e:
                    self._bl.exception(f"Failed to load from pdf: {str(e)}")
            elif extension.endswith("geojson") or "geojson" in extension or \
                "geo+json" in extension:
                try:
                    return self._load_geojson
                except Exception as e:
                    self._bl.exception(f"Failed to load from geojson: {str(e)}")
                
            elif extension.endswith("txt") or "txt" in extension or \
                "text/csv" in extension or "text/plain" in extension:
                try:
                    return self._load_text
                except Exception as e:
                    self._bl.exception(f"Failed to load from text: {str(e)}")
    

    def load_data(self):
        """Loads data from a specified URL or file path.

        This method attempts to load data from either a URL (self.doc_url) or a local file path (self.file_path).
        It supports various file formats including CSV, XLSX, XLS, ODS, PDF, and JSON based on the file extension or the Content-Type header 
        if fetched from a URL.  The data is then parsed and returned accordingly.  Handles GitHub URLs by urlsplit and urljoin methods.

        Returns:
            dict or list or None:  Returns a dictionary containing dataframes for each sheet in Excel files (.xls, .xlsx, .ods), 
                                a list of dictionaries for CSV files, a dictionary for JSON files, or None if the file type is unsupported or an error occurs.
                                For ODS files, the keys are the sheet names. For CSV files, the keys are the lowercase versions of column names with spaces replaced by underscores.
                                PDF files are returned as pdfplumber.PDF

        Raises:
            Various exceptions:  Exceptions may be raised during file I/O, data parsing, or network requests 
                           depending on the file type and source.  Error messages are printed to the console.
        """
        try:
            extension = self._extension
            if not extension and self.doc_url:
                guessed_extension = self._guess_extension()
                self._supported_extensions.append(guessed_extension)
                self._extension = guessed_extension
                return self._load_for_extension
            else:
                return self._load_for_extension
            
        except Exception as e:
            self._bl.exception(f"Failed to load data\nReason: {str(e)}")
            return None
        

class PostProcess:
    def __init__(self, debug:bool=False):
        self._debug = debug
        self._bl = BasicLogger(verbose=False, 
                               log_directory=None, 
                               logger_name="POST_PROCESS", 
                               log_level = logging.DEBUG if self._debug else logging.INFO)

    @staticmethod
    def find_year_from_year_str(year_str: str) -> str:
        """
        Extracts the ending year from a year range string or single year string.
        
        The function handles ranges separated by hyphens (e.g., '2021-22' or '1995-1996').
        If a two-digit end year is provided, it infers the century from the start year.
        If no range is present, it attempts to return the first 4-digit sequence found.

        Args:
            year_str: A string representing a year or year range (e.g., "2020-21", "2023").

        Returns:
            A string representing the full 4-digit end year. Returns the original 
            string if no numeric patterns are identified.

        Examples:
            >>> find_year_from_year_str("2021-22")
            '2022'
            >>> find_year_from_year_str("1998-1999")
            '1999'
            >>> find_year_from_year_str("2024")
            '2024'
        """
        if not year_str or not isinstance(year_str, str):
            return str(year_str) if year_str else ""
        
        # Split by hyphen and clean whitespace
        parts = [p.strip() for p in year_str.split("-") if p.strip()]
        
        if not parts:
            return year_str
        
        # Case: Single year string (e.g., "2023")
        if len(parts) == 1:
            match = re.search(r"\d{4}", parts[0])
            return match.group() if match else parts[0]

        # Case: Range (e.g., "2021-22" or "2021-2022")
        first_part = parts[0]
        last_part = parts[-1]
        
        # Extract digits from the end of the range
        match = re.search(r"\d+", last_part)
        if not match:
            return first_part 
        
        end_year_digits = match.group()
        
        # If the end year is only 2 digits (e.g., "22"), prefix it with 
        # the century from the start year (e.g., "20")
        if len(end_year_digits) == 2 and len(first_part) >= 2:
            century = first_part[:2] 
            return f"{century}{end_year_digits}"
        
        return end_year_digits

    @staticmethod
    def set_columns_from_index_and_drop_rows(df:pd.DataFrame,
                col_index:Union[int, str, List[str], List[int]],
               year_row_index:Optional[Union[str,int]]=None):

        col_index_list = None
        if isinstance(col_index, (int,str)):
            col_index_list = [int(col_index)]
        elif isinstance(col_index, list):
            col_index_list = [int(x) for x in col_index]
        else:
            raise TypeError("Index must be an int, str, or list of ints/strs")

        # 1. Extract and fill header rows
        header_rows = df.iloc[col_index_list]
        with pd.option_context('future.no_silent_downcasting', True):
            header_data_filled = header_rows.ffill(axis=1).infer_objects(copy=False)

        # 2. Create the MultiIndex
        new_columns = pd.MultiIndex.from_arrays(header_data_filled.values)

        # 3. Clean the year level if requested
        if year_row_index is not None:
            # If the user passed a row label or index that corresponds to the list,
            # we need the POSITION (0, 1, 2...) within our new MultiIndex levels.
            # Since index_list is positional, we find where year_row_index sits in it.
            try:
                level_pos = col_index_list.index(int(year_row_index))
            except ValueError:
                # Fallback: if year_row_index is already 0, 1, 2 (level pos)
                level_pos = int(year_row_index)

            # Extract current labels for that level
            raw_years = new_columns.get_level_values(level_pos)

            # Clean them using your function
            cleaned_years = [PostProcess.find_year_from_year_str(str(y)) for y in raw_years]

            # Update the MultiIndex level
            new_columns = new_columns.set_levels(cleaned_years, level=level_pos)

        # 4. Finalize DataFrame
        _bl = BasicLogger(verbose=False, log_directory=None, logger_name="POST_PROCESS")
        df_clean = df.drop(col_index_list)
        if len(df_clean.columns) != len(new_columns):
            _bl.warning(f"Number of columns in DataFrame does not match number of columns in MultiIndex.  \
                DataFrame has {len(df_clean.columns)} columns, MultiIndex has {len(new_columns)} columns.")
            return None
        if len(col_index_list)==1:
            df_clean.columns = [x[0] for x in new_columns]
        else:
            df_clean.columns = new_columns
        return df_clean
        
    @staticmethod
    def _set_columns_from_index_and_drop_rows(df:pd.DataFrame, 
                                             col_index:Union[str, int])->Optional[pd.DataFrame]:
        """Sets DataFrame columns from a specified row and drops rows above that row.

        This function takes a Pandas DataFrame and an integer index as input.  It uses the row at the specified index as the new column names for the DataFrame.  All rows above the specified index are then dropped. Finally, it cleans the column names by removing leading digits and whitespace, converting to lowercase, and replacing spaces with underscores.

        Args:
            df (pd.DataFrame): The input Pandas DataFrame.
            col_index (int): The index of the row to use as new column names.

        Returns:
            pd.DataFrame: A new DataFrame with updated column names and rows above `col_index` dropped.  Returns None if `col_index` is out of bounds.

        Raises:
            IndexError: If `col_index` is out of bounds for the DataFrame.

        """
        col_index = int(col_index)

        df_copy = df.copy()
        df_copy.columns = df_copy.iloc[col_index]
        df_copy = df_copy.iloc[col_index + 1:,].reset_index(drop=True)
        df_copy.columns = [re.sub(r"\d+\.?\s+?", "", str(col).lower()).replace(" ", "_") for col in df_copy.columns]
        return df_copy


    @staticmethod
    def convert_data_types_of_cols(df:pd.DataFrame, d_type:str, debug:bool=False)->Optional[pd.DataFrame]:
        """Converts data types of columns in a DataFrame.

        This function takes a Pandas DataFrame and a data type as input.  It converts all columns in the DataFrame to the specified data type.  If the data type is not supported, it raises a TypeError.

        Args:
            df (pd.DataFrame): The input Pandas DataFrame.
            d_type (str): The data type to convert the columns to.  Must be one of 'float', 'int', or 'category'.
            debug (bool, optional): Whether to enable debug logging. Defaults to False.

        Returns:
            pd.DataFrame: A new DataFrame with all columns converted to the specified data type.  Returns None if the data type is not supported.

        Raises:
            TypeError: If the data type is not supported.

        """

        d_type_lower = d_type.lower()
        if  d_type_lower not in ["float", "int", "category"]:
            raise TypeError(f"Invalid data type '{d_type}'. Choose from 'float, int'")
        
        post_process = PostProcess(debug=debug)
        df_copy = df.copy()
        
        for col in df_copy.columns:
            post_process._bl.debug(f"Processing column: '{col}'")
            try:
                df_copy[col] = df_copy[col].astype(d_type_lower)
                post_process._bl.debug(f"Column: '{col}' converted to data type '{d_type}'.")
            except:
                post_process._bl.debug(f"Processing failed for column: '{col}'. Retaining original data type")
                df_copy[col] = df_copy[col]
        
        return df_copy
    
    

    

    



            

    

        

        

                

            


        