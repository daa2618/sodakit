from __future__ import annotations

from .data_loader import Dataset, BasicLogger, logging

import datetime
import re
from pathlib import Path

from typing import Optional, List, Any

#_bl = ErrorOnlyLogger(verbose = False, log_directory=None, logger_name = "DATA VERSION")
_bl = BasicLogger(verbose = False, log_directory=None, logger_name = "DATA_VERSION")
class DatesNotFound(Exception):
    pass

class FileVersion:
    """
    Represents a file version with a specified base path, file name, extension, and date format.

    Args:
        base_path (str): The base path where the file is located.
        file_name (str): The name of the file (without extension).
        extension (str): The file extension (including the leading dot, e.g., ".txt").
        date_fmt (str, optional): The format string for the date part of the file name, 
                                    following strftime conventions. Defaults to "%m%d%Y".

    Attributes:
        base_path (str): The base path.
        file_name (str): The file name.
        extension (str): The file extension.
        date_fmt (str): The date format string. 
    """
    def __init__(self, 
                 base_path:Path,
                 file_name:str,
                extension:str,
                date_fmt:str="%m%d%Y", 
                
                #**kwargs
                ):
        self.base_path = Path(base_path)
        self.file_name = f"{file_name}_" if not file_name.endswith("_") else file_name
        self.extension = f".{extension}" if not extension.startswith(".") else extension
        self.date_fmt = date_fmt
        #super().__init__(**kwargs)
    
    
    def folder_exists(self)->bool:
        """Ensures that the specified base path folder exists.

        Creates the folder and its parent directories if they don't exist.  
        Always returns True, indicating that the function has either confirmed 
        the folder's existence or created it.

        Args:
            self: The instance of the class containing the `base_path` attribute.  
                `base_path` should be a string representing the path to the folder.

        Returns:
            bool: True.  Always returns True, regardless of whether the folder 
                already existed or was newly created.
        """

        #if not os.path.exists(self.base_path):
        #    os.makedirs(self.base_path)
        self.base_path.mkdir(exist_ok=True, parents=True)
        return True
            
    def get_all_files(self)->List[Path]:
        """Retrieves all files matching a specific filename pattern within a base path.

        This method checks if the base path exists. If it does, it returns a list of 
        filenames within that path that contain the specified filename (self.file_name). 
        If the base path does not exist, it returns None.

        Returns:
            list: A list of strings representing the filenames that match the pattern, 
                    or None if the base path does not exist.  Returns an empty list if 
                    the path exists but no matching files are found.
        """
        if self.folder_exists():
            file_paths = [file_path for file_path in \
                          self.base_path.glob(f"*{self.extension}") if \
                            file_path.is_file() and self.file_name in file_path.name]
            return file_paths
            #return [x for x in os.listdir(self.base_path) if self.file_name in x]
        else:
            return None
    
    def file_exists(self)->bool:
        """Checks if any files with matching filename exist in the associated data source.

        This method indirectly checks for the existence of files with filename by attempting to retrieve a list of all files.  
        If `get_all_files()` returns an empty list (indicating no files found), it returns `False`. Otherwise, it returns `True`.

        Returns:
            bool: True if at least one file exists, False otherwise.
        """
        if not self.get_all_files():
            return False
        else:
            return True
    
    def make_file_name(self)->str:
        """Generates a file name with a timestamp.

    This method constructs a file name by combining the base file name, 
    a timestamp formatted according to a specified date format, and a file extension.

    Args:
        self: The instance of the class containing the file name components.  Must have attributes:
            - file_name (str): The base name of the file.
            - date_fmt (str): The format string for the datetime object (e.g., "%Y%m%d_%H%M%S").  Should be compatible with `datetime.strftime`.
            - extension (str): The file extension (e.g., ".txt", ".csv").

    Returns:
        str: The generated file name, including the timestamp and extension.  For example, if file_name="data", date_fmt="%Y%m%d", extension=".csv", and the current date is 2024-10-27, the returned string would be "data20241027.csv".

    Raises:
        AttributeError: If any of the required attributes (file_name, date_fmt, extension) are missing from the self object.
    """
        return f'{self.file_name}{datetime.datetime.strftime(datetime.datetime.now(), self.date_fmt)}{self.extension}'
    
    def _search_for_dates(self)->Optional[List[str]]:
        """Extracts numerical date components from a filename.

        This function extracts all sequences of digits from the filename generated by 
        the `self.make_file_name()` method.  It first removes hyphens, underscores, and 
        percentage signs from the filename before performing the extraction. This is 
        useful for extracting date components (e.g., year, month, day) that might be 
        embedded within a filename using these separators.

        Returns:
            list: A list of strings, where each string represents a sequence of digits 
                    found in the modified filename.  These strings will need further 
                    processing to be interpreted as dates if needed.  Returns an empty list
                    if no digits are found.

        Example:
            If self.make_file_name() returns "data_2024-10-26_report.txt", the function 
            will return ['2024', '10', '26'].
        """
        #return re.split(pattern="[-_+%]", string=self.make_file_name())[-1]
        return re.findall("[0-9]+", re.sub("[-_%]", "", self.make_file_name()))
        
        
    def check_version(self)->Any:
        """Checks the version of files in a specified folder.

        This method checks if a folder exists. If it does, it identifies the latest file 
        based on its name (assuming a date-based naming convention). It then compares 
        the date of the latest file to the current date. If the latest file's date is 
        older than today, it returns `True`; otherwise, it returns `False`.  If the folder 
        doesn't exist, it creates the folder.  The function handles potential errors 
        during file date extraction and comparison.  It also cleans up older files in the 
        folder, keeping only the latest one.

        The date format is determined by the `self.date_fmt` attribute.  File names are 
        assumed to contain a date component that can be parsed according to this format.
        The file extension is defined by `self.extension`.

        Args:
            None (Uses self attributes: `self.folder_exists`, `self.base_path`, `self.date_fmt`, `self.extension`)

        Returns:
            bool: `True` if the latest file's date is older than today, `False` otherwise.
                    Returns `True` if any error occurs during file processing.

        Raises:
            None:  Exceptions are caught internally; the function returns `True` in case of failure.
        """
        if self.folder_exists:
            dates = self._fetch_dates_from_file_names()
            all_files = [f"{self.file_name}{datetime.datetime.strftime(x, self.date_fmt)}{self.extension}" for x in dates]
            #all_files=self.get_all_files()
            if len(all_files) > 1:
                for file in all_files[:-1]:
                    file_path_to_remove = self.base_path.joinpath(file)
                    try:
                        file_path_to_remove.unlink()
                    except Exception as e:
                        _bl.error(f"Failed to remove file '{file}' from {self.base_path}", e)
                        continue
                    #os.remove(os.path.join(self.base_path, file))
            try:
                
                dates = self._fetch_dates_from_file_names()
                date = dates[-1]
                now = datetime.datetime.now()
                now = datetime.datetime(now.year, now.month, now.day)
                if date < now:
                    return True
                else:
                    return False
            except:
                return True
        else:
            #os.makedirs(self.base_path)
            self.base_path.mkdir(exist_ok=True, parents=True)
        
    def _get_file_path(self)->Optional[Path]:
        """Retrieves the file path if the folder and file exist and the version is correct.

        This method checks if the designated folder and file exist within the specified base path.  
        It also verifies the file version using `self.check_version()`. If all conditions are met, 
        it returns the full path to the first file found in the folder; otherwise, it returns None.

        Returns:
            str: The full file path if the folder and file exist and the version is correct.  Returns the path of the first file found in the folder.
            None: If the folder or file does not exist, or if the version check fails.
        """
        if self.folder_exists() and self.file_exists():
            if not self.check_version():
                #return os.path.join(self.base_path, self.get_all_files()[0])
                all_files = self.get_all_files()
                if all_files:
                    return all_files[0]
                else:
                    return None
        else:
            return None
        
    @property    
    def _latest_file_path(self)->Optional[Path]:
        """
        Returns the absolute path to the latest file in the specified data folder.

        This property searches for files matching a specific pattern (fileName_ followed by numbers and the specified extension) within the base_path.  It identifies the latest file based on the numerical part of the filename, assuming this represents a timestamp or version number.  The date is extracted and formatted.  Handles cases where the filename does not follow the expected pattern.

        Returns:
            str: The absolute path to the latest file if found, otherwise None.  Prints informative messages about the data folder and file details.  If no matching file is found, returns None.

        Raises:
            Exception: If there's an issue converting the extracted date string to a datetime object.  Note that the specific exception type isn't caught, making debugging more difficult.  Consider improving exception handling to provide more specific error messages.
        """
        self.folder_exists()
        _bl.info(f"\tData folder: '{self.base_path}'\n\tFilename: '{self.file_name}'\n\tExtension: '{self.extension}'")

        #latest_file=[x for x in os.listdir(self.base_path) if self.file_name in x and x.endswith(self.extension)][-1]
        if not self.file_name.endswith("_"):
            self.file_name = f"{self.file_name}_"
        
        pattern = re.compile(f"{self.file_name}[0-9]+{self.extension}")
        #latest_file=[x for x in os.listdir(self.base_path) if pattern.findall(x)]
        latest_file = [file_path for file_path in self.base_path.glob(f"*{self.extension}") if file_path.is_file() and pattern.findall(file_path.name)]
        if latest_file:
            
            latest_file=latest_file[-1]
            last_file_name = latest_file.name
            date = re.split(pattern="[-_+%]", string=last_file_name)
            if len(date) == 1:
                date = re.findall("[0-9]+", last_file_name)
            date = re.sub(f"{self.extension}", "", date[-1])

            #date = datetime.datetime.strptime(date[0], self.date_fmt)
            try:
                date = datetime.datetime.strptime(date, self.date_fmt)
            except:
                date = re.findall("[0-9]+", date)[0]
                date = datetime.datetime.strptime(date, self.date_fmt)

            date=datetime.datetime.strftime(date, "%d %b %Y")

            print(f"\n\tThe file was downloaded on '{date}'\n")

            return latest_file#os.path.abspath(os.path.join(self.base_path, latest_file))
        else:
            return None
    
    
    def _fetch_dates_from_file_names(self, sort_order:str="ascending")->Optional[List[datetime.datetime]]:
        if not self.file_name.endswith("_"):
            self.file_name = f"{self.file_name}_"
        
        file_name = re.sub("\\(", "\\(?", self.file_name)
        file_name = re.sub("\\)", "\\)?", file_name)
        dateFormatSub=re.sub(r"%m|%Y|%d|%H|%M|%S", r"[0-9]+", self.date_fmt)
        dateFormatSub=re.sub(r"%b|%B", "[a-zA-Z]+", dateFormatSub)

        pattern = re.compile(f"\\b{file_name}{dateFormatSub}{self.extension}")
        #pattern = re.compile(f"\\b{file_name}[0-9]+{self.extension}")
        latest_file_paths = [file_path for file_path in \
                             self.base_path.glob(f"*{self.extension}") if \
                                file_path.is_file() and pattern.findall(file_path.name)]
        if latest_file_paths:
            dates = [re.sub(f"{file_name}|\\{self.extension}", "", file_path.name) for file_path in latest_file_paths]
            dates = sorted([datetime.datetime.strptime(date, self.date_fmt) for date in dates], 
                           reverse=True if sort_order.lower() == "descending" else False)
            #dates.sort(key=sort_order.lower())
            #dates.sort()
            return dates
        else:
            raise DatesNotFound("No dates found for any of the matching file names in the directory")
    
    def sort_files_by_date(self, sort_order:str="ascending")->List[Path]:
        sort_order_lower = sort_order.lower()
        if sort_order_lower not in {"ascending", "descending"}:
            raise TypeError("Incorrect sort order. select from 'ascending' or 'descending'")

        dates_found = self._fetch_dates_from_file_names(sort_order=sort_order_lower)
        if not dates_found:
            return
        
        date_str = [datetime.datetime.strftime(date, self.date_fmt) for date in dates_found]
        fp = [self.base_path/f"{self.file_name}{date_str}{self.extension}" for date_str in date_str]
        return fp

    def get_latest_n_files(self, n:int):
        try:
            sorted_files = self.sort_files_by_date()
            return sorted_files[-n:]
        except Exception as e:
            _bl.error(f"Failed to get latest {n} files", e)
            return 
    
    @property    
    def latest_file_path(self)->Optional[Path]:
        """
        Returns the absolute path to the latest file in the specified data folder.

        This property searches for files matching a specific pattern (fileName_ followed by numbers and the specified extension) within the base_path.  It identifies the latest file based on the numerical part of the filename, assuming this represents a timestamp or version number.  The date is extracted and formatted.  Handles cases where the filename does not follow the expected pattern.

        Returns:
            str: The absolute path to the latest file if found, otherwise None.  Prints informative messages about the data folder and file details.  If no matching file is found, returns None.

        Raises:
            Exception: If there's an issue converting the extracted date string to a datetime object.  Note that the specific exception type isn't caught, making debugging more difficult.  Consider improving exception handling to provide more specific error messages.
        """
        self.folder_exists()
        _bl.info(f"\tData folder: '{self.base_path}'\n\tFilename: '{self.file_name}'\n\tExtension: '{self.extension}'")

        #latest_file=[x for x in os.listdir(self.base_path) if self.file_name in x and x.endswith(self.extension)][-1]
        try:
            dates = self._fetch_dates_from_file_names()

            latest_date = dates[-1]
            latest_date_str = datetime.datetime.strftime(latest_date, self.date_fmt)
            fp = f"{self.file_name}{latest_date_str}{self.extension}"
            date=datetime.datetime.strftime(latest_date, "%d %b %Y")

            _bl.info(f"\n\tThe file was downloaded on '{date}'\n")

            return self.base_path.joinpath(fp)#os.path.abspath(os.path.join(self.base_path, fp))
        except Exception as e:
            _bl.error("Failed to get latest file path", e)
            return None



    def load_latest_file(self, class_name, func, check_version=False, **kwargs):
        from .data_writer import WriteFile
        """Loads data from the latest file matching a specified pattern.

        This function checks for the existence of a file matching a given file name and 
        extension in a specified base path. If a file exists, it attempts to parse a date 
        from the filename.  If the date is older than today, a new file is created using 
        data generated by a provided function, then the data from the newest file is loaded.
        If no file exists, a new file is created and its data is loaded.

        Args:
            class_name: The class containing the data generation function.
            func: The name of the function (string) within the class_name that generates the data to be written. This function should accept **kwargs.
            check_version: A boolean indicating whether to check the file version before writing (passed to WriteFile). Defaults to False.
            **kwargs: Keyword arguments passed to the data generation function (func).

        Returns:
            A Dataset object containing the loaded data from the latest file.

        Raises:
            Various exceptions can occur during file operations (e.g., FileNotFoundError, OSError) or if the date parsing fails.  The function uses bare 'except:' blocks which mask potential errors; this should be improved for production code to provide more specific error handling.
        """
        #file = FileVersion(base_path, file_name, extension)
        self.folder_exists()

        try:

            dates = self._fetch_dates_from_file_names()
            date = dates[-1]
            now = datetime.datetime.now()
            now = datetime.datetime(now.year, now.month, now.day)
            if date < now:
                WriteFile(data_to_write=getattr(class_name, func)(**kwargs),
                         base_path=self.base_path,
                         file_name=self.file_name,
                         extension=self.extension).write_file_to_disk(check_version)
            #latest_file=[x for x in os.listdir(self.base_path) if self.file_name in x and x.endswith(self.extension)][-1]
            #file_path=os.path.join(self.base_path, latest_file)
            latest_file = self.latest_file_path
            return Dataset(file_path=latest_file).load_data()
        except Exception as e:
            _bl.error("Failed to load latest file", e)

            WriteFile(data_to_write=getattr(class_name, func)(**kwargs),
                         base_path=self.base_path,
                         file_name=self.file_name,
                         extension=self.extension).write_file_to_disk(check_version)
            #latest_file=[x for x in os.listdir(self.base_path) if self.file_name in x and x.endswith(self.extension)][-1]
            #file_path=os.path.join(self.base_path, latest_file)
            file_path=self.latest_file_path
            return Dataset(file_path=file_path).load_data()
