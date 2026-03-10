#!/usr/bin/env python3
"""Command-line interface for ShareBib."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .client import ShareBibClient
from .exceptions import ShareBibError

CommandHandler = Callable[[ShareBibClient, argparse.Namespace], int]


def to_jsonable(value: Any) -> Any:
    """Convert SDK return values into JSON-serializable data."""
    if is_dataclass(value):
        return {key: to_jsonable(val) for key, val in asdict(value).items()}
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(val) for key, val in value.items()}
    return value


def print_json(value: Any) -> None:
    """Print a JSON payload to stdout."""
    print(json.dumps(to_jsonable(value), indent=2, ensure_ascii=False))


def auth_info(client: ShareBibClient, args: argparse.Namespace) -> int:
    del args
    print_json(client.auth_info())
    return 0


def users_search(client: ShareBibClient, args: argparse.Namespace) -> int:
    print_json(client.search_users(args.q, limit=args.limit))
    return 0


def collections_list(client: ShareBibClient, args: argparse.Namespace) -> int:
    del args
    print_json(client.list_collections())
    return 0


def collections_create(client: ShareBibClient, args: argparse.Namespace) -> int:
    result = client.create_collection(
        title=args.title,
        description=args.description,
        visibility=args.visibility,
        tags=args.tag or [],
        collection_id=args.id,
    )
    print_json(result)
    return 0


def collections_info(client: ShareBibClient, args: argparse.Namespace) -> int:
    print_json(client.get_collection(args.id))
    return 0


def collections_delete(client: ShareBibClient, args: argparse.Namespace) -> int:
    client.delete_collection(args.id)
    print_json({"ok": True, "collection_id": args.id})
    return 0


def collections_export_bibtex(client: ShareBibClient, args: argparse.Namespace) -> int:
    content = client.export_collection_bibtex(args.id)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        print_json(
            {
                "ok": True,
                "collection_id": args.id,
                "output": str(output_path),
                "bytes": len(content.encode("utf-8")),
            }
        )
        return 0

    if content.endswith("\n"):
        print(content, end="")
    else:
        print(content)
    return 0


def collections_permissions_list(
    client: ShareBibClient, args: argparse.Namespace
) -> int:
    print_json(client.list_collection_permissions(args.id))
    return 0


def collections_permissions_add(
    client: ShareBibClient, args: argparse.Namespace
) -> int:
    result = client.set_collection_permission(
        args.id,
        user_id=args.user_id,
        permission=args.permission,
    )
    print_json(result)
    return 0


def collections_permissions_remove(
    client: ShareBibClient, args: argparse.Namespace
) -> int:
    client.remove_collection_permission(args.id, args.user_id)
    print_json({"ok": True, "collection_id": args.id, "user_id": args.user_id})
    return 0


def papers_add(client: ShareBibClient, args: argparse.Namespace) -> int:
    result = client.add_paper(
        collection_id=args.collection_id,
        title=args.title,
        authors=args.author or [],
        venue=args.venue,
        year=args.year,
        abstract=args.abstract,
        summary=args.summary,
        arxiv_id=args.arxiv_id,
        doi=args.doi,
        url_arxiv=args.url_arxiv,
        url_pdf=args.url_pdf,
        url_code=args.url_code,
        url_project=args.url_project,
        tags=args.tag or [],
    )
    print_json(result)
    return 0


def papers_list(client: ShareBibClient, args: argparse.Namespace) -> int:
    print_json(client.list_papers(args.collection_id))
    return 0


def papers_search(client: ShareBibClient, args: argparse.Namespace) -> int:
    print_json(
        client.search_papers(
            args.q,
            limit=args.limit,
            year=args.year,
            status=args.status,
        )
    )
    return 0


def papers_info(client: ShareBibClient, args: argparse.Namespace) -> int:
    print_json(client.get_paper(args.id))
    return 0


def papers_remove(client: ShareBibClient, args: argparse.Namespace) -> int:
    client.remove_paper(args.collection_id, args.id)
    print_json({"ok": True, "collection_id": args.collection_id, "paper_id": args.id})
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""
    parser = argparse.ArgumentParser(
        description="Operate ShareBib collections and papers from the command line.",
    )
    parser.add_argument("--api-key", help="ShareBib API key (starts with pc_)")
    parser.add_argument(
        "--base-url",
        help="ShareBib base URL, e.g. https://papers.example.com",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--config",
        help="Path to a ShareBib config file (JSON)",
    )

    subparsers = parser.add_subparsers(dest="command")

    auth_parser = subparsers.add_parser("auth", help="Authentication-related commands")
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command")

    auth_info_parser = auth_subparsers.add_parser(
        "info", help="Show information about the current API key"
    )
    auth_info_parser.set_defaults(handler=auth_info)

    users_parser = subparsers.add_parser("users", help="User lookup operations")
    users_subparsers = users_parser.add_subparsers(dest="users_command")

    users_search_parser = users_subparsers.add_parser(
        "search", help="Search users by username"
    )
    users_search_parser.add_argument("--q", required=True, help="Search query")
    users_search_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results",
    )
    users_search_parser.set_defaults(handler=users_search)

    collections_parser = subparsers.add_parser(
        "collections", help="Collection operations"
    )
    collections_subparsers = collections_parser.add_subparsers(
        dest="collections_command"
    )

    collections_list_parser = collections_subparsers.add_parser(
        "list", help="List accessible collections"
    )
    collections_list_parser.set_defaults(handler=collections_list)

    collections_create_parser = collections_subparsers.add_parser(
        "create", help="Create a collection"
    )
    collections_create_parser.add_argument(
        "--title", required=True, help="Collection title"
    )
    collections_create_parser.add_argument(
        "--description",
        default="",
        help="Collection description",
    )
    collections_create_parser.add_argument(
        "--visibility",
        default="private",
        choices=["private", "public", "public_editable"],
        help="Collection visibility",
    )
    collections_create_parser.add_argument(
        "--tag",
        action="append",
        help="Collection tag (repeatable)",
    )
    collections_create_parser.add_argument(
        "--id",
        help="Optional custom collection ID",
    )
    collections_create_parser.set_defaults(handler=collections_create)

    collections_info_parser = collections_subparsers.add_parser(
        "info", help="Show collection details"
    )
    collections_info_parser.add_argument("--id", required=True, help="Collection ID")
    collections_info_parser.set_defaults(handler=collections_info)

    collections_delete_parser = collections_subparsers.add_parser(
        "delete", help="Delete a collection"
    )
    collections_delete_parser.add_argument("--id", required=True, help="Collection ID")
    collections_delete_parser.set_defaults(handler=collections_delete)

    collections_export_parser = collections_subparsers.add_parser(
        "export-bibtex", help="Export a collection as BibTeX"
    )
    collections_export_parser.add_argument("--id", required=True, help="Collection ID")
    collections_export_parser.add_argument(
        "--output",
        help="Optional output file path. If omitted, prints BibTeX to stdout.",
    )
    collections_export_parser.set_defaults(handler=collections_export_bibtex)

    collections_permissions_parser = collections_subparsers.add_parser(
        "permissions", help="Manage collection sharing permissions"
    )
    collections_permissions_subparsers = collections_permissions_parser.add_subparsers(
        dest="collections_permissions_command"
    )

    collections_permissions_list_parser = collections_permissions_subparsers.add_parser(
        "list", help="List effective permissions for a collection"
    )
    collections_permissions_list_parser.add_argument(
        "--id", required=True, help="Collection ID"
    )
    collections_permissions_list_parser.set_defaults(
        handler=collections_permissions_list
    )

    collections_permissions_add_parser = collections_permissions_subparsers.add_parser(
        "add", help="Grant or replace a collection permission"
    )
    collections_permissions_add_parser.add_argument(
        "--id", required=True, help="Collection ID"
    )
    collections_permissions_add_parser.add_argument(
        "--user-id", required=True, help="Target user ID"
    )
    collections_permissions_add_parser.add_argument(
        "--permission",
        required=True,
        choices=["view", "edit"],
        help="Permission to grant",
    )
    collections_permissions_add_parser.set_defaults(handler=collections_permissions_add)

    collections_permissions_remove_parser = (
        collections_permissions_subparsers.add_parser(
            "remove", help="Remove a user's explicit permission"
        )
    )
    collections_permissions_remove_parser.add_argument(
        "--id", required=True, help="Collection ID"
    )
    collections_permissions_remove_parser.add_argument(
        "--user-id", required=True, help="Target user ID"
    )
    collections_permissions_remove_parser.set_defaults(
        handler=collections_permissions_remove
    )

    papers_parser = subparsers.add_parser("papers", help="Paper operations")
    papers_subparsers = papers_parser.add_subparsers(dest="papers_command")

    papers_add_parser = papers_subparsers.add_parser(
        "add", help="Create a paper and add it to a collection"
    )
    papers_add_parser.add_argument(
        "--collection-id",
        required=True,
        help="Target collection ID",
    )
    papers_add_parser.add_argument("--title", required=True, help="Paper title")
    papers_add_parser.add_argument(
        "--author", action="append", help="Author name (repeatable)"
    )
    papers_add_parser.add_argument("--venue", help="Venue name")
    papers_add_parser.add_argument("--year", type=int, help="Publication year")
    papers_add_parser.add_argument("--abstract", help="Paper abstract")
    papers_add_parser.add_argument("--summary", help="Paper summary")
    papers_add_parser.add_argument("--arxiv-id", help="arXiv identifier")
    papers_add_parser.add_argument("--doi", help="Paper DOI")
    papers_add_parser.add_argument("--url-arxiv", help="arXiv URL")
    papers_add_parser.add_argument("--url-pdf", help="PDF URL")
    papers_add_parser.add_argument("--url-code", help="Code repository URL")
    papers_add_parser.add_argument("--url-project", help="Project page URL")
    papers_add_parser.add_argument(
        "--tag", action="append", help="Paper tag (repeatable)"
    )
    papers_add_parser.set_defaults(handler=papers_add)

    papers_list_parser = papers_subparsers.add_parser(
        "list", help="List papers in a collection"
    )
    papers_list_parser.add_argument(
        "--collection-id",
        required=True,
        help="Collection ID",
    )
    papers_list_parser.set_defaults(handler=papers_list)

    papers_search_parser = papers_subparsers.add_parser(
        "search", help="Search accessible papers"
    )
    papers_search_parser.add_argument("--q", required=True, help="Search query")
    papers_search_parser.add_argument(
        "--limit", type=int, default=50, help="Maximum number of results"
    )
    papers_search_parser.add_argument(
        "--year", type=int, help="Filter by publication year"
    )
    papers_search_parser.add_argument(
        "--status",
        help="Filter by paper status, e.g. accessible or no_access",
    )
    papers_search_parser.set_defaults(handler=papers_search)

    papers_info_parser = papers_subparsers.add_parser("info", help="Show paper details")
    papers_info_parser.add_argument("--id", required=True, help="Paper ID")
    papers_info_parser.set_defaults(handler=papers_info)

    papers_remove_parser = papers_subparsers.add_parser(
        "remove", help="Remove a paper from a collection"
    )
    papers_remove_parser.add_argument(
        "--collection-id",
        required=True,
        help="Collection ID",
    )
    papers_remove_parser.add_argument("--id", required=True, help="Paper ID")
    papers_remove_parser.set_defaults(handler=papers_remove)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    handler: CommandHandler | None = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 1

    try:
        client = ShareBibClient(
            api_key=args.api_key,
            base_url=args.base_url,
            timeout=args.timeout,
            config_path=Path(args.config) if args.config else None,
        )
        return handler(client, args)
    except ShareBibError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
