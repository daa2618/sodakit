"""Command-line interface for sodakit."""
from __future__ import annotations

import argparse
import json
import logging
import sys

import dotenv

from sodakit.api import MoreSocrata, MoreSocrataData
from sodakit.exceptions import DatasetNotFound, OrganizationNotFound

# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _format_table(rows: list[dict]) -> str:
    """Format a list of dicts as a plain-text table."""
    if not rows:
        return "(no results)"
    headers = list(rows[0].keys())
    col_widths = {h: len(str(h)) for h in headers}
    str_rows = []
    for row in rows:
        str_row = {h: str(row.get(h, "")) for h in headers}
        for h in headers:
            col_widths[h] = max(col_widths[h], len(str_row[h]))
        str_rows.append(str_row)

    # Cap column width at 60 chars
    for h in headers:
        col_widths[h] = min(col_widths[h], 60)

    def _trunc(val, width):
        return val[:width - 1] + "\u2026" if len(val) > width else val.ljust(width)

    lines = []
    header_line = "  ".join(_trunc(str(h), col_widths[h]) for h in headers)
    lines.append(header_line)
    lines.append("  ".join("-" * col_widths[h] for h in headers))
    for sr in str_rows:
        lines.append("  ".join(_trunc(sr[h], col_widths[h]) for h in headers))
    return "\n".join(lines)


def _format_list(items: list, header: str | None = None) -> str:
    """Format a flat list, one item per line."""
    if not items:
        return "(no results)"
    lines = []
    if header:
        lines.append(header)
        lines.append("-" * len(header))
    for item in items:
        lines.append(str(item))
    return "\n".join(lines)


def _format_dict(data: dict) -> str:
    """Format a dict as key-value pairs."""
    if not data:
        return "(no results)"
    max_key = max(len(str(k)) for k in data)
    lines = []
    for k, v in data.items():
        lines.append(f"{str(k).ljust(max_key)}  {v}")
    return "\n".join(lines)


def _output(data, *, json_mode: bool):
    """Print data in the requested format."""
    if json_mode:
        print(json.dumps(data, indent=2, default=str))
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        print(_format_table(data))
    elif isinstance(data, list):
        print(_format_list(data))
    elif isinstance(data, dict):
        print(_format_dict(data))
    else:
        print(data)


# ---------------------------------------------------------------------------
# Client helpers
# ---------------------------------------------------------------------------

def _make_base_client(args) -> MoreSocrata:
    """Create a MoreSocrata instance from parsed args."""
    return MoreSocrata(
        domain=args.domain,
        domain_id=args.domain_id,
        app_token=args.app_token,
        username=args.username,
        password=args.password,
    )


def _make_data_client(args, dataset_id: str | None = None) -> MoreSocrataData:
    """Create a MoreSocrataData instance from parsed args."""
    did = dataset_id or getattr(args, "dataset_id", None)
    return MoreSocrataData(
        domain=args.domain,
        domain_id=args.domain_id,
        app_token=args.app_token,
        username=args.username,
        password=args.password,
        dataset_id=did,
    )


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

_LIST_TARGETS = {
    "datasets": ("ALL_DATASET_NAMES", "Datasets"),
    "agencies": ("ALL_AGENCIES", "Agencies"),
    "categories": ("ALL_CATEGORIES", "Categories"),
    "tags": ("ALL_DOMAIN_TAGS", "Domain Tags"),
    "types": ("ALL_DATA_TYPES", "Data Types"),
}


def _handle_list(args):
    client = _make_base_client(args)
    prop, header = _LIST_TARGETS[args.list_target]
    data = _apply_limit_sort(list(getattr(client, prop)), args)
    if args.json_mode:
        _output(data, json_mode=True)
    else:
        print(_format_list(data, header=header))


def _handle_search(args):
    client = _make_data_client(args)
    target = args.search_target
    if target == "datasets":
        results = client.search_available_datasets(args.name)
    elif target == "tags":
        results = client.search_available_domain_tags(args.tag)
    elif target == "agencies":
        results = client.search_agencies(args.agency)
    else:
        print(f"Unknown search target: {target}", file=sys.stderr)
        sys.exit(1)
    results = _apply_limit_sort(results, args)
    _output(results, json_mode=args.json_mode)


def _handle_get_id(args):
    client = _make_data_client(args)
    result = client.get_dataset_id_for_dataset_name(args.name)
    _output(result, json_mode=args.json_mode)


def _handle_load(args):
    client = _make_data_client(args)
    limit = args.limit if args.limit else False
    data = client.try_loading_dataset(print_description=args.describe, limit=limit)
    _output(data, json_mode=args.json_mode)


def _handle_query(args):
    client = _make_data_client(args)
    result = client.query_dataset(args.sql)
    _output(result, json_mode=args.json_mode)


def _handle_columns(args):
    client = _make_data_client(args)
    result = client.get_column_description_for_dataset()
    _output(result, json_mode=args.json_mode)


def _handle_filter(args):
    client = _make_data_client(args)
    target = args.filter_target
    if target == "tag":
        results = client.filter_data_for_domain_tags(args.tag)
    elif target == "type":
        results = client.filter_datasets_for_data_type(args.type)
    elif target == "agency":
        results = client.filter_datasets_for_agency(args.agency)
    else:
        print(f"Unknown filter target: {target}", file=sys.stderr)
        sys.exit(1)
    results = _apply_limit_sort(results, args)
    _output(results, json_mode=args.json_mode)


# ---------------------------------------------------------------------------
# Shared parser helpers
# ---------------------------------------------------------------------------

def _add_limit_sort_args(parser):
    """Add --limit and --sort flags to a sub-parser."""
    parser.add_argument("--limit", type=int, default=0, help="Max number of items to display")
    parser.add_argument("--sort", action="store_true", help="Sort items alphabetically")


def _apply_limit_sort(data, args):
    """Apply --sort and --limit to a list of results."""
    if not isinstance(data, list):
        return data
    if args.sort:
        data = sorted(data, key=lambda x: str(x).casefold())
    if args.limit:
        data = data[:args.limit]
    return data


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sodakit",
        description="CLI for exploring and querying Socrata Open Data API datasets.",
    )

    # Global options
    parser.add_argument("--domain", required=True, help="Socrata domain (e.g. data.cityofnewyork.us)")
    parser.add_argument("--domain-id", required=True, help="Short domain identifier (e.g. NYC)")
    parser.add_argument("--app-token", default=None, help="Socrata app token (default: $APP_TOKEN)")
    parser.add_argument("--username", default=None, help="Socrata username (default: $USERNAME)")
    parser.add_argument("--password", default=None, help="Socrata password (default: $PASSWORD)")
    parser.add_argument("--json", action="store_true", dest="json_mode", help="Output as JSON")

    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # -- list --
    list_parser = subparsers.add_parser("list", help="List all items of a given type")
    list_sub = list_parser.add_subparsers(dest="list_target", required=True)
    for target in _LIST_TARGETS:
        p = list_sub.add_parser(target)
        _add_limit_sort_args(p)

    # -- search --
    search_parser = subparsers.add_parser("search", help="Fuzzy search datasets, tags, or agencies")
    search_sub = search_parser.add_subparsers(dest="search_target", required=True)
    p = search_sub.add_parser("datasets", help="Search dataset names")
    p.add_argument("name", help="Search term")
    _add_limit_sort_args(p)
    p = search_sub.add_parser("tags", help="Search domain tags")
    p.add_argument("tag", help="Search term")
    _add_limit_sort_args(p)
    p = search_sub.add_parser("agencies", help="Search agencies")
    p.add_argument("agency", help="Search term")
    _add_limit_sort_args(p)

    # -- get-id --
    p = subparsers.add_parser("get-id", help="Get dataset ID for an exact dataset name")
    p.add_argument("name", help="Exact dataset name")

    # -- load --
    p = subparsers.add_parser("load", help="Load a dataset by ID")
    p.add_argument("--dataset-id", required=True, help="Socrata dataset identifier (e.g. abcd-1234)")
    p.add_argument("--limit", type=int, default=0, help="Max rows to return")
    p.add_argument("--describe", action="store_true", help="Print column descriptions")

    # -- query --
    p = subparsers.add_parser("query", help="Run a SoQL query on a dataset")
    p.add_argument("--dataset-id", required=True, help="Socrata dataset identifier")
    p.add_argument("sql", help="SoQL query string")

    # -- columns --
    p = subparsers.add_parser("columns", help="Show column descriptions for a dataset")
    p.add_argument("--dataset-id", required=True, help="Socrata dataset identifier")

    # -- filter --
    filter_parser = subparsers.add_parser("filter", help="Filter datasets by tag, type, or agency")
    filter_sub = filter_parser.add_subparsers(dest="filter_target", required=True)
    p = filter_sub.add_parser("tag", help="Filter by domain tag")
    p.add_argument("tag", help="Exact domain tag")
    _add_limit_sort_args(p)
    p = filter_sub.add_parser("type", help="Filter by data type")
    p.add_argument("type", help="Data type (e.g. dataset, map, chart)")
    _add_limit_sort_args(p)
    p = filter_sub.add_parser("agency", help="Filter by agency name")
    p.add_argument("agency", help="Exact agency name")
    _add_limit_sort_args(p)

    return parser


_HANDLERS = {
    "list": _handle_list,
    "search": _handle_search,
    "get-id": _handle_get_id,
    "load": _handle_load,
    "query": _handle_query,
    "columns": _handle_columns,
    "filter": _handle_filter,
}


def main(argv: list[str] | None = None) -> None:
    """Entry point for the sodakit CLI."""
    dotenv.load_dotenv()

    # Suppress verbose INFO logs from internal loggers when running as CLI
    for name in ("MORE_SOCRATA", "DATA_VERSION"):
        logging.getLogger(name).setLevel(logging.WARNING)

    parser = _build_parser()
    args = parser.parse_args(argv)

    handler = _HANDLERS.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    try:
        handler(args)
    except (DatasetNotFound, OrganizationNotFound) as exc:
        if args.json_mode:
            print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        else:
            print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
