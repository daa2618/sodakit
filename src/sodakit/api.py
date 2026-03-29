from __future__ import annotations

import datetime
import itertools
import os
from pathlib import Path
from urllib.parse import quote

import dotenv
import geopandas as gpd
from sodapy import Socrata

from sodakit.utils.data_loader import Dataset
from sodakit.utils.data_version import FileVersion
from sodakit.utils.log_helper import BasicLogger
from sodakit.utils.response import Response
from sodakit.utils.strings import _get_unique_elements, get_matching_scores_for_string, stemmer

from .exceptions import DatasetNotFound, OrganizationNotFound


class MoreSocrata:

    """
    A class for interacting with the  OpenData Socrata API.

    This class simplifies accessing data from the  OpenData portal using the Socrata Python client.  It handles authentication and provides a foundation for retrieving datasets.

    Attributes:
        domain (str): The domain of the  OpenData Socrata instance (eg. "data.cityofnewyork.us").
        domain_id (str) : domain identifier (eg. "NYC")
        domain_url (str) : The url of the  OpenData Website
        _creds (_Socrata_Client): An instance of a helper class managing API credentials.
        _client (Socrata): An instance of the Socrata Python client, authenticated and ready to make API calls.
        _ALL_DATASETS (list or None):  A cache to store all datasets (initially None, populated on demand).  This helps to avoid redundant API calls.

    Methods:
        __init__(): Initializes the class with API credentials and establishes a connection to the Socrata API.
        (Other methods would be added here to interact with the API, such as fetching specific datasets or performing queries.)

    Example:
        nyc_data = MoreSocrata("data.cityofnewyork.us")  # Initialize the class
        # ... further interaction with the API using _data object ...

    """
    dotenv.load_dotenv()

    def __init__(self,
                 domain:str,
                 domain_id:str,
                 app_token:str=None,
                 username:str=None,
                 password:str=None):

        self.domain = domain
        self.domain_id = domain_id
        self.domain_url = f"https://{self.domain}/"
        self._app_token = app_token if app_token else os.environ.get("APP_TOKEN")
        self._username = username if username else os.environ.get("USERNAME")
        self._password = password if password else os.environ.get("PASSWORD")

        self._client = Socrata(
            domain = self.domain,
            app_token=self._app_token,
            username=self._username,
            password=self._password,
            timeout=30
        )
        self._ALL_DATASETS = None
        self.data_path = Path("data").absolute()
        self._logger = BasicLogger(verbose = False, log_directory=None, logger_name = "MORE_SOCRATA")
        self._logger.info(f"DATA_DIRECTORY: {self.data_path}")
        self._domain_dataset_dir = self.data_path/domain_id

    def _get_all_datasets_in_api(self):

        return self._client.datasets()


    @property
    def _ALL_DATASETS_IN_DOMAIN(self):
        """
        Retrieves all datasets within the specified domain.

        This property lazily loads a list of datasets from a JSON file 
        (allDatasets_.json) located in the `self.data_path`.  If the data 
        hasn't been loaded yet, it attempts to load it using the 
        `_get_all_datasets_in_api` method, checking the file version.  If 
        the file is not found or loading fails, it prints a message and 
        returns None.

        Returns:
            list: A list of datasets (dictionaries) for the domain, or None if no data is found.
        """
        if self._ALL_DATASETS is None:
            file = FileVersion(base_path=self._domain_dataset_dir,
                            file_name=f"all{self.domain_id}Datasets_",
                            extension="json")
            datasets = file.load_latest_file(self, "_get_all_datasets_in_api", check_version=False)
            if datasets:
                #self._logger.info(f"{len(datasets)} datasets have been found at the domain '{self.domain}'")
                self._ALL_DATASETS = datasets
            else:
                self._logger.error("No datasets info could be found")
        return self._ALL_DATASETS

    @property
    def ALL_DATASET_NAMES(self):
        """
        Returns a list of all dataset names within the current domain.

        This property iterates through the internal list `_ALL_DATASETS_IN_DOMAIN` 
        and extracts the 'name' attribute from the 'resource' dictionary of each dataset.

        Returns:
            list: A list of strings, where each string represents the name of a dataset.  Returns an empty list if `_ALL_DATASETS_IN_DOMAIN` is empty or None.
            """
        datasets_in_domain = self._ALL_DATASETS_IN_DOMAIN
        if datasets_in_domain:

            dataset_names = sorted([
                x.get("resource").get("name") for x in datasets_in_domain
            ])
            #dataset_names.sort()
            return dataset_names
        else:
            return []

    @property
    def ALL_CATEGORIES(self):
        """Returns a unique list of all categories across all datasets in the domain.

        This property iterates through all datasets in the `_ALL_DATASETS_IN_DOMAIN` attribute,
        extracts the 'categories' list from each dataset's 'classification' dictionary, 
        and then flattens and deduplicates the resulting list of categories.

        Returns:
            list: A list of unique strings representing all categories found across all datasets.  Returns an empty list if `_ALL_DATASETS_IN_DOMAIN` is empty or contains no categories.
        """

        cats = [
            x.get("classification").get("categories") for x in self._ALL_DATASETS_IN_DOMAIN
        ]
        return _get_unique_elements(cats)

    @property
    def ALL_AGENCIES(self):
        """Returns a list of unique agencies present in all datasets within the domain.

        This property iterates through all datasets in the domain (self._ALL_DATASETS_IN_DOMAIN) 
        and extracts the agency values from their classification metadata.  It then uses 
        the _get_unique_elements helper function to return only unique agency names.

        Returns:
            list: A list of strings, where each string represents a unique agency name.  
                Returns an empty list if no agencies are found or if self._ALL_DATASETS_IN_DOMAIN is empty.
        """
        agencies = [
            [y.get("value") for y in x.get("classification").get("domain_metadata") \
            if "agency" in y.get("key").lower()] for x in self._ALL_DATASETS_IN_DOMAIN
        ]
        return _get_unique_elements(agencies)

    @property
    def ALL_DOMAIN_CATEGORIES(self):
        """
        Returns a list of unique domain categories across all datasets in the domain.

        This property iterates through all datasets within the domain (accessible via `self._ALL_DATASETS_IN_DOMAIN`)
        and extracts the 'domain_category' from each dataset's 'classification' dictionary.  It then uses the
        `_get_unique_elements` function (assumed to be defined elsewhere) to return only the unique categories.

        Returns:
            list: A list of unique strings representing the domain categories.  Returns an empty list if 
                  `self._ALL_DATASETS_IN_DOMAIN` is empty or if no domain categories are found.
        """
        domainCats = [
            x.get("classification").get("domain_category") for x in self._ALL_DATASETS_IN_DOMAIN
        ]
        return _get_unique_elements(domainCats)

    @property
    def ALL_DOMAIN_TAGS(self):
        """
        Returns a list of unique domain tags across all datasets within the domain.

        This property iterates through all datasets in the domain (accessed via `self._ALL_DATASETS_IN_DOMAIN`)
        and extracts the 'domain_tags' from their 'classification' dictionaries.  Duplicate tags are removed,
        resulting in a list containing only unique domain tags.

        Returns:
            list: A list of unique strings representing the domain tags.  Returns an empty list if 
                `self._ALL_DATASETS_IN_DOMAIN` is empty or no domain tags are found.
        """
        domainTags = [
            x.get("classification").get("domain_tags") for x in self._ALL_DATASETS_IN_DOMAIN
        ]
        return _get_unique_elements(domainTags)

    @property
    def ALL_DATA_TYPES(self):
        """
        Returns a list of unique data types present in all datasets within the domain.

        This property iterates through all datasets in the domain (accessed via `self._ALL_DATASETS_IN_DOMAIN`) 
        and extracts the data type from each dataset's resource.  It then uses the `_get_unique_elements` 
        function to return only the unique data types.

        Returns:
            list: A list of unique strings representing the data types found in the datasets.  Returns an empty list if `self._ALL_DATASETS_IN_DOMAIN` is empty or contains no valid data types.
        """
        dTypes = [
            x.get("resource").get("type") for x in self._ALL_DATASETS_IN_DOMAIN
        ]
        return _get_unique_elements(dTypes)


class MoreSocrataData(MoreSocrata):

    """
    A class extending MoreSocrata to provide enhanced functionality for accessing and manipulating  Socrata data.

    This class inherits from the `MoreSocrata` class (a base class providing core Socrata API interaction) and adds 
    features specific to working with  datasets.  It may include methods for data cleaning, transformation, 
    specialized querying, or other operations tailored to the characteristics of 's open data.

    Attributes:
        (Inherited from MoreSocrata:  These will depend on the implementation of the parent class)

    Args:
        **kwargs: Keyword arguments passed to the constructor.  
        Must include 'dataset_id' specifying the ID of the Socrata  dataset.

    Methods:
        (Methods specific to this class will be documented individually.  These may include but are not limited to:
         data cleaning, filtering, specific query construction, data type conversion etc.)

    """


    def __init__(self, domain, domain_id, **kwargs):
        super().__init__(domain, domain_id,
                         app_token=kwargs.get("app_token"),
                         username=kwargs.get("username"),
                         password=kwargs.get("password"))
        self.dataset_id = kwargs.get("dataset_id")

    def _get_resource_for_dataset(self):
        """Retrieves the resource associated with a dataset ID.

        This method searches through a list of all datasets within a domain 
        (`self._ALL_DATASETS_IN_DOMAIN`) to find the resource corresponding to the 
        dataset ID stored in `self.dataset_id`.

        Args:
            None

        Returns:
            list: A list containing the resource dictionary if a match is found.  
                The list will contain only one element if a match is found.  Returns an empty list if no match is found.

        Raises:
            DatasetNotFound: If no dataset with the specified ID is found within the domain.
        """
        if self.dataset_id:
            resource_for_id = [x.get("resource") for x in self._ALL_DATASETS_IN_DOMAIN if x.get("resource").get("id") == self.dataset_id]
            if resource_for_id:
                return resource_for_id

            else:
                raise DatasetNotFound("No matching dataset was found for given dataset ID")
        else:
            self._logger.warning("Please input dataset ID while initiating the class")

    def _get_metadata_for_dataset(self):
        """Retrieves metadata for the specified dataset.

        This method retrieves metadata associated with the dataset ID provided 
        during class instantiation.  If no dataset ID was provided, it raises a 
        message indicating to provide a dataset ID. If a dataset ID is provided 
        but no metadata is found, a `DatasetNotFound` exception is raised.

        Returns:
            dict: A dictionary containing the metadata for the dataset, if found.

        Raises:
            DatasetNotFound: If no metadata is found for the given dataset ID.
            Exception: If no dataset_id was provided during class instantiation.
        """
        if self.dataset_id:
            metadata = self._client.get_metadata(dataset_identifier=self.dataset_id)
            if metadata:
                return metadata
            else:
                raise DatasetNotFound("No meta data found for given dataset ID")
        else:
            self._logger.warning("Please input dataset ID while initiating the class")

    def get_column_description_for_dataset(self):
        """Retrieves column descriptions for a dataset.

        This method fetches column names and their corresponding descriptions 
        from a data source based on the dataset ID provided during class initialization.

        Returns:
            dict: A dictionary where keys are column names (strings) and values are 
                    their descriptions (strings). Returns an empty dictionary if no 
                    descriptions are found.  Returns None if the dataset ID is not set 
                    or if multiple datasets match the ID.

        Raises:
            KeyError: If more than one dataset matches the provided dataset ID.
        """
        if self.dataset_id:
            resource_for_id = self._get_resource_for_dataset()
            if resource_for_id and len(resource_for_id) == 1:
                resource_for_id = resource_for_id[0]

            else:
                raise KeyError("More than one dataset match for given ID")

            cols_dict=dict(zip(resource_for_id.get("columns_field_name"),
                            resource_for_id.get("columns_description")))
            if cols_dict:
                return cols_dict
            else:
                self._logger.error("No column description could be found for the dataset with given ID")
                return None
        else:
            self._logger.warning("Please input dataset ID while initiating the class")
            return None

    def try_loading_dataset(self, print_description:bool=False, limit:bool=False):
        """
        Attempts to load a dataset from a Socrata API.

        This function tries to retrieve a dataset based on a previously set dataset ID.  It handles different dataset types 
        (file, map) and provides options for limiting the number of rows retrieved and printing a description.  It raises 
        exceptions for various error conditions.

        Args:
            print_description (bool, optional): If True, prints the dataset description. Defaults to False.
            limit (int, optional): use `limit=n` where `n` is the integer. Defaults to False.,
                                limits the number of rows retrieved (only applicable for certain dataset types).
             
        Returns:
            str or list or None:  Returns the download URL for file datasets, a list of URLs for map datasets, 
                                a list of records for other datasets if successful, None otherwise.


        Raises:
            KeyError: If more than one dataset matches the given ID.
            MemoryError: If the dataset is too large (over 1,000,000 rows) for a JSON retrieval.  Consider filtering the data before querying.
            Exception: For any other errors encountered during API calls.  The specific error message is printed to the console.

        Notes:
        - This function requires a dataset ID to be set prior to calling (via class initialization).
        - File and map datasets are downloaded via URLs; this function only provides these URLs.
        - For large datasets, consider using the `limit` parameter or filtering your query to reduce the amount of data processed.

        """
        if self.dataset_id:
            resource_for_id = self._get_resource_for_dataset()
            meta_data = self._get_metadata_for_dataset()
            if resource_for_id and len(resource_for_id) == 1:
                resource_for_id = resource_for_id[0]
            else:
                raise KeyError("More than one dataset match for given ID")


            dataset_name, dataset_description = resource_for_id.get("name"), resource_for_id.get("description")
            self._logger.info("="*127)
            parent_id = resource_for_id.get("parent_fxf")
            self._logger.info(f"Visit {self.domain_url}/resource/{self.dataset_id} for more information")
            if parent_id and len(parent_id) == 1:
                    parent_id = parent_id[0]
                    self._logger.info(f"Alternatively, Visit {self.domain_url}/resource/{parent_id} for more information on the parent data")
            self._logger.info(f"Trying to fetch the data for '{dataset_name}' from {self.domain}....")
            if print_description:
                self._logger.info(f"Data Description: \n\t{dataset_description}\n")

            n_rows = [x.get("cachedContents").get("count") for x in meta_data.get("columns") if x.get("cachedContents") is not None]
            n_rows = [x for x in n_rows if x is not None]

            if n_rows:
                n_rows = max([int(x) for x in n_rows])
                self._logger.info(f"The Dataset consits of '{n_rows:,}' rows\n")
            else:
                self._logger.info("Number of rows was not found for the dataset in meta data")

            d_type = resource_for_id.get("type")
            self._logger.info(f"Data type of the required file: {d_type}\n")

            if d_type == "file":
                blob=resource_for_id.get("blob_mime_type").split("application/")
                if blob:
                    blob = blob[-1]
                    download_url = f"{self.domain_url}download/{self.dataset_id}/application%2F{blob}"
                    self._logger.info(f"For this file format, Socrata does not return a json value\nDownload the file from '{download_url}' instead")

                    self._logger.info("="*127)
                    return download_url
                else:
                    self._logger.info(f"No blob data found. Check {blob}")
                    self._logger.info("="*127)
                    return None
            elif d_type == "map":
                urls = []
                if parent_id:



                    urls.append(f"{self.domain_url}api/views/{parent_id}/rows.csv?date={datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')}&accessType=DOWNLOAD")
                    urls.append(f"{self.domain_url}api/geospatial/{parent_id}?method=export&format=GeoJSON")
                    urls.append(f"{self.domain_url}api/views/{parent_id}/rows.csv?accessType=DOWNLOAD")
                    urls.append(f"{self.domain_url}api/views/{parent_id}/rows.json?accessType=DOWNLOAD")
                else:
                    urls.append(f"{self.domain_url}api/views/{self.dataset_id}/rows.csv?date={datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')}&accessType=DOWNLOAD")
                    urls.append(f"{self.domain_url}api/geospatial/{self.dataset_id}?method=export&format=GeoJSON")
                    urls.append(f"{self.domain_url}api/views/{self.dataset_id}/rows.csv?accessType=DOWNLOAD")
                    urls.append(f"{self.domain_url}api/views/{self.dataset_id}/rows.json?accessType=DOWNLOAD")

                self._logger.info("For this file format, Socrata does not return a json value\nDownload the file from the urls instead")
                self._logger.info("="*127)
                return urls


            else:
                self._logger.info("Fetching the data using the API...")
                data = None
                if limit:
                    try:
                        data = self._client.get(dataset_identifier=self.dataset_id, limit=limit)
                    except Exception as e:
                        self._logger.error(f"Failed to fetch dataset with limit: {e}")

                else:

                    if n_rows and n_rows > 1000000:
                        raise MemoryError("The file size may be too big to get json;\n\tConsider filtering before querying")

                    try:
                        data = list(self._client.get_all(dataset_identifier=self.dataset_id))
                    except Exception as e:
                        self._logger.error(f"Failed to fetch all records: {e}")

                if not data:
                    if parent_id:

                        json_url = f"{self.domain_url}/resource/{parent_id}.json"
                        try:
                            response = Response(json_url).get_json_from_response()
                        except Exception as e:
                            self._logger.error(f"Failed to fetch parent resource: {e}")
                            response = None
                        if response:

                            self.dataset_id = parent_id
                            meta = self._get_metadata_for_dataset()
                            n_rows = [x.get("cachedContents").get("count") for x in meta.get("columns") if x.get("cachedContents") is not None]
                            n_rows = [x for x in n_rows if x is not None]
                            if n_rows:
                                n_rows = max([int(x) for x in n_rows])
                                if n_rows == len(response):
                                    self._logger.info("The data was successfully obtained")
                                else:
                                    try:
                                        _data_client = self._client.get(dataset_identifier=self.dataset_id, limit=n_rows)
                                    except Exception:
                                        _data_client = None

                                    if _data_client:
                                        self._logger.info("The data was successfully obtained")
                                        return _data_client

                                    self._logger.info("Returning data\nCheck the site to see if the data is complete")

                            url=f"{self.domain_url}api/views/{parent_id}/rows.csv?date={datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')}&accessType=DOWNLOAD"
                            self._logger.info(f"Alternatively, Click the url {url} to download the data")
                            self._logger.info("="*127)
                            return response


                if data:
                    data = [x for x in data if x]
                    if data:
                        self._logger.info("The data was successfully obtained")
                        self._logger.info("="*127)
                        return data
                    else:
                        self._logger.error(f"Unable to fetch the data from API")

                        self._logger.info(f"Visit {self.domain_url}/resource/{self.dataset_id} for more information")
                        if parent_id:
                            url=f"{self.domain_url}api/views/{parent_id}/rows.csv?date={datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')}&accessType=DOWNLOAD"
                            self._logger.info(f"Alternatively, Click the url {url} to download the data")
                        self._logger.info("="*127)
                        return None
                else:
                    self._logger.error(f"Unable to fetch the data from API")
                    self._logger.info("="*127)
                    return None




        else:
            self._logger.info("Please input dataset ID while initiating the class")
            return None

    def _search_list_by_string(self, search_list:list, search_string:str):
        """Searches a list of strings for a given search string using stemming and score matching.

        This function attempts to find strings in `search_list` that match `search_string`.
        It first performs stemming on both the search string and the list elements and checks for exact matches.
        If no exact matches are found, it calculates similarity scores using `get_matching_scores_for_string` 
        and returns strings with a score of 0.5 or higher.  If no matches are found using either method, it returns None.

        Args:
            search_list (list): A list of strings to search within.
            search_string (str): The string to search for.

        Returns:
            list or None: A list of strings from `search_list` that match `search_string` (either exactly after stemming or with a similarity score >= 0.5), or None if no matches are found.  The returned list will be a subset of the input search_list.

        Note:
            This function relies on an external `stemmer` object (presumably a stemming algorithm) and a `get_matching_scores_for_string` function (presumably a function to calculate string similarity scores).  These must be defined elsewhere in the code.
        """
        filtered=[x for x in search_list if stemmer.stem(search_string) in stemmer.stem(x)]
        if filtered:
            return filtered
        else:
            matching_scores = get_matching_scores_for_string(search_list, search_string)
            score_indices=[True if x >= 0.5 else False for x in matching_scores]
            filtered=[search_list[x] for x in list(itertools.compress(range(len(score_indices)),
                                                                     score_indices))]
            if filtered:
                return filtered
            else:
                return None

    def search_available_datasets(self, dataset_name:str) ->list:
        """Searches for dataset names matching a given string.

        Args:
            dataset_name: The string to search for within dataset names.

        Returns:
            A list of dataset names whose names contain the search string.  
            Returns an empty list if no matches are found.

        Raises:
            DatasetNotFound: If no organizations match the search string.
        """

        filtered=self._search_list_by_string(self.ALL_DATASET_NAMES, dataset_name)
        if filtered:
            return filtered
        else:
            raise DatasetNotFound("No matching datasets could be found")


    def get_dataset_id_for_dataset_name(self, abs_dataset_name:str) -> str:
        """Retrieves the dataset ID associated with a given absolute dataset name.

        Searches within the internal list `self._ALL_DATASETS_IN_DOMAIN` for a dataset 
        whose name matches the provided `abs_dataset_name`.

        Args:
            abs_dataset_name: The absolute name of the dataset to search for.

        Returns:
            str or list or None: 
            - If exactly one dataset matches the name, returns its ID (str).
            - If multiple datasets match, returns a list of their IDs.
            - If no dataset matches, raises a `DatasetNotFound` exception.
            - If a matching dataset is found but lacks an ID, prints a message and returns None.

        Raises:
    
            DatasetNotFound: If no dataset with the given name is found.
        """

        matched_for_name = [x for x in self._ALL_DATASETS_IN_DOMAIN \
                          if x.get("resource").get("name") == abs_dataset_name]
        if matched_for_name:
            if len(matched_for_name) == 1:
                dataset_id = matched_for_name[0].get("resource").get("id")
                if dataset_id:
                    return dataset_id
                else:
                    self._logger.error("No dataset ID was found for the dataset")
                    return None
            else:
                self._logger.warning(f"More than one dataset match for given name '{abs_dataset_name}'")
                return [x.get("resource").get("id") for x in matched_for_name]
                #raise KeyError(f"More than one dataset match for given name '{abs_dataset_name}'")
        else:
            raise DatasetNotFound(f"No dataset found for name '{abs_dataset_name}'")

    def search_available_domain_tags(self, search_tag:str) ->list:
        """Searches for domain tags matching a given search string.

        Args:
            search_tag: The string to search for within the available domain tags.

        Returns:
            A list of domain tags that contain the search string.  Returns an empty list if no matches are found.

        Raises:
            KeyError: If no domain tags matching the search string are found.
        """

        filtered=self._search_list_by_string(self.ALL_DOMAIN_TAGS, search_tag)
        if filtered:
            return filtered
        else:
            raise KeyError("No matching tags could be found")


    def _fetch_data_from_matched_resources(self, matched_results:list):
        """
        Processes a list of matched resource results and returns a formatted list of dictionaries.

        Args:
            matched_results (list): A list of dictionaries, where each dictionary represents a matched resource 
                                and contains nested "resource" and "permalink" keys.  The "resource" key 
                                should contain at least "name", "id", "type", "createdAt", "data_updated_at", 
                                and "updated_at" keys.

        Returns:
            list: A list of dictionaries, where each dictionary represents a processed resource with the 
                following keys: "dataset_name", "dataset_id", "data_type", "data_created_at", "data_updated_at", 
                "updated_at", and "resource_url".  Date fields are converted to a consistent string format 
                ("%d %B %Y %H:%M:%S") and missing or invalid dates are replaced with the minimum datetime. 
                The list is sorted in descending order based on the "data_updated_at" field.  Returns an unsorted list if sorting fails.


        Raises:
            None:  Exceptions during sorting are caught and printed to console, but not re-raised.
        """
        matched_res = [dict(
            dataset_name=x.get("resource").get("name"),
            dataset_id=x.get("resource").get("id"),
            data_type=x.get("resource").get("type"),
            data_created_at = x.get("resource").get("createdAt"),
            data_updated_at = x.get("resource").get("data_updated_at"),
            updated_at = x.get("resource").get("updated_at"),

            resource_url = x.get("permalink")
            )\
        for x in matched_results]

        for x in matched_res:
            for date_col in ["data_created_at", "data_updated_at", "updated_at"]:
                if not x[date_col] or not isinstance(x[date_col], str):
                    x[date_col] = (datetime.datetime.min).replace(tzinfo=datetime.timezone.utc)
                if isinstance(x[date_col], str):
                    x[date_col] = datetime.datetime.strftime(datetime.datetime.fromisoformat(x[date_col]), "%d %B %Y %H:%M:%S")
                elif isinstance(x[date_col], datetime.datetime):
                    x[date_col] = datetime.datetime.strftime(x[date_col], "%d %B %Y %H:%M:%S")

        key = lambda x: datetime.datetime.strptime(x.get("data_updated_at"), "%d %B %Y %H:%M:%S")

        try:
            matched_res.sort(key=key, reverse=True)
        except Exception as e:
            self._logger.warning("Sorting by date unsuccessful")
        self._logger.info(f"{len(matched_res)} matched results were found and sorted by the latest data updated date\n")
        return matched_res


    def filter_data_for_domain_tags(self, search_tag:str) -> list:
        """Filters datasets based on a given domain tag.

       This function searches for datasets within a domain that contain specific domain tags. 
        It retrieves matching datasets, formats their information, handles potential date inconsistencies, 
        sorts the results by the 'data_updated_at' field, and returns a list of dictionaries.  Each dictionary
        represents a dataset with relevant attributes.

        Args:
            search_tag (str): The domain tag to search for.

        Returns:
            list: A list of dictionaries, where each dictionary contains information about a dataset 
              that matches the search tag.  The dictionaries include keys: `dataset_name`, `dataset_id`,
              `data_type`, `data_created_at`, `data_updated_at`, `updated_at`, and `resource_url`. Date values
              are formatted as strings "dd Month YYYY HH:MM:SS". Returns an empty list if no datasets are found.

        Raises:
            DatasetNotFound: If no datasets match the search tag.  This exception is raised if either the initial search for tags
                         or the subsequent search for datasets yields no results.
        """
        matched_tags = self.search_available_domain_tags(search_tag)
        if matched_tags:
            matched_results_for_tag = [x for x in self._ALL_DATASETS_IN_DOMAIN if any(tag in x.get("classification").get("domain_tags") for tag in matched_tags)]
            if matched_results_for_tag:
                matched_res = self._fetch_data_from_matched_resources(matched_results_for_tag)

            else:
                raise DatasetNotFound("No matching dataset was found with given domain tag")

            return matched_res
        else:
            raise DatasetNotFound("No matching dataset was found with given domain tag")


    def filter_datasets_for_data_type(self, d_type:str) -> list:
        """Filters a list of datasets to return only those matching a specified data type.

        Args:
            d_type (str): The data type to filter by.

        Returns:
            list: A list of datasets matching the specified data type, or None if no matches are found after fetching data.  Returns an empty list if no matches are found before fetching data.

        Raises:
            DatasetNotFound: If the specified data type is not available or if no datasets with the specified data type are found in the domain.  The error message includes a list of available data types.
        """
        if not d_type in self.ALL_DATA_TYPES:
            raise DatasetNotFound(f"Data type mismatch\nAvailable types: {','.join(self.ALL_DATA_TYPES)}")


        matched_results_for_d_type = [x for x in self._ALL_DATASETS_IN_DOMAIN if x.get("resource").get("type") == d_type]
        if not matched_results_for_d_type:
            raise DatasetNotFound("No data with required data type was found in domain")
        else:
            res = self._fetch_data_from_matched_resources(matched_results_for_d_type)
            if res:
                return res
            else:
                return None

    def search_agencies(self, agency:str) -> list:
        """Searches for agencies matching a given string.

        Args:
            agency (str): The string to search for within agency names.

        Returns:
            list: A list of unique agencies whose names contain the search string.  Returns an empty list if no matches are found.

        Raises:
            OrganizationNotFound: If no agency matching the search string is found.
        """
        matched_agencies = self._search_list_by_string(self.ALL_AGENCIES, agency)
        if not matched_agencies:
            raise OrganizationNotFound("No agency responsible for data was found for given string")
        else:
            return _get_unique_elements(matched_agencies)

    def filter_datasets_for_agency(self, abs_agency_name:str) -> list:
        """Filters datasets to retrieve only those associated with a specific agency.

        Args:
            abs_agency_name (str): The exact name of the agency to filter by.  
                                This must be an absolute agency name as it exists within the system.

        Returns:
            list: A list of datasets associated with the specified agency. Returns None if no datasets are found or if the agency name is invalid.

        Raises:
            OrganizationNotFound: If the provided agency name is not found in the system's registry.
            DatasetNotFound: If no datasets are associated with the specified agency.

        Notes:
            - If multiple agencies match the input `abs_agency_name`, a message is printed indicating the matching agencies. The function will then raise an OrganizationNotFound exception.  The user needs to provide the exact agency name.
            - The function uses internal methods `self.search_agencies` and `self._fetch_data_from_matched_resources` for searching agencies and retrieving dataset details.
        """
        if not abs_agency_name in self.ALL_AGENCIES:
            matched_agencies = self.search_agencies(abs_agency_name)
            if matched_agencies:
                self._logger.info(f"More than one matching agencies found\nResults: {', '.join(matched_agencies)}\nChoose one and try again")
            else:
                raise OrganizationNotFound("Agency not found.Use absolute agency names")

        matched_res= None
        matchedForAgency = [
            x for x in self._ALL_DATASETS_IN_DOMAIN if abs_agency_name in [
                y.get("value") \
                    for y in x.get("classification").get("domain_metadata")
                    ]
                    ]
        if not matchedForAgency:
            raise DatasetNotFound("No dataset was found for agency")
        else:
            matched_res = self._fetch_data_from_matched_resources(matchedForAgency)

        if matched_res:
            return matched_res
        else:
            return None

    def query_dataset(self,query:str):
        """Queries a dataset based on a provided query string.

        Args:
            query (str): The query string to use for filtering the dataset.  This string will be URL-encoded.

        Returns:
            dict or None: A dictionary containing the queried data if successful, otherwise None.  
                        Returns None if the dataset_id has not been set.

        Raises:
            Various Exceptions:  Catches and prints any exceptions encountered during the API request.  The specific exception type is not explicitly handled.

        Notes:
            This function requires that the `dataset_id` and `domain_url` attributes of the class instance are set before calling this function.  
            If `dataset_id` is not set, it prints an error message and returns None.  
            The query string is appended to the URL as a parameter using URL encoding.
        """
        if self.dataset_id:
            url=f"{self.domain_url}/resource/{self.dataset_id}.json"
            params=f"$query={quote(query)}"
            try:
                queried_data = Response(url=url,
                                       params=params).get_json_from_response()

            except Exception as e:
                self._logger.error("Failed to get json response", e)
                queried_data = None

            return queried_data

        else:
            self._logger.warning("Initiate by setting dataset id")
            return None

    def load_geo_data(self, geo_url:str):
        if "csv" in geo_url:
            data = Dataset(doc_url=geo_url).load_data()
            if data:
                return data
        elif "geojson" in geo_url.lower():

            return gpd.read_file(geo_url)
        else:
            raise TypeError(f"Supported geo datatypes: CSV or geojson")









































