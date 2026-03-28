from __future__ import annotations

from difflib import SequenceMatcher
from nltk.stem.snowball import SnowballStemmer
import itertools

stemmer = SnowballStemmer("english")

def get_matching_scores_for_string(strings_list:list, check_for_string:str):
    """Calculates the similarity ratio between a string and a list of strings.

    This function iterates through a list of strings and computes the similarity ratio 
    of each string to a specified string using the SequenceMatcher.ratio() method.  
    The comparison is case-insensitive.  Empty strings in the input list are ignored.

    Args:
        strings_list: A list of strings to compare against.
        check_for_string: The string to compare each string in strings_list against.

    Returns:
        A list of floats. Each float represents the similarity ratio (between 0 and 1 inclusive) 
        of a string from strings_list to check_for_string.  The order of ratios corresponds to 
        the order of strings in strings_list (excluding empty strings).  Returns an empty list if 
        strings_list is empty or contains only empty strings.
    """
    return [SequenceMatcher(None, x.lower(), check_for_string.lower()).ratio() for x in strings_list if x]


def _get_unique_elements(list_of_elems:list)->list:
    """Returns a sorted list of unique elements from the input list.

    Args:
        list_of_elems: A list of elements.  Can contain nested lists.

    Returns:
        A new list containing only the unique elements from list_of_elems, 
        sorted in ascending order.

    Raises:
        ValueError: If the input list is empty.
    """
    if list_of_elems:
        if any(isinstance(x, list) for x in list_of_elems):
            unique_elems = list(set(itertools.chain.from_iterable(list_of_elems)))
        else:
            unique_elems = list(set(list_of_elems))
        unique_elems = [x for x in unique_elems if x]
        unique_elems.sort()
        return unique_elems
    else:
        raise ValueError("List should not be empty")