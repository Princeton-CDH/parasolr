"""
**index** is a custom manage command to index content into Solr.  It
should only be run *after* your schema has been configured via
**solr_schema**.

By default, indexes _all_ indexable content.

You can optionally index specific items by type or by index id.  Default
index types are generated based on model verbose names.

A progress bar will be displayed by default if there are more than 5
items to process.  This can be suppressed via script options.

You may optionally request the index or part of the index to be cleared
before indexing, for use when index data has changed sufficiently that
previous versions need to be removed.

Example usage::

    # index everything
    python manage.py index
    # index specific items
    python manage.py index person:1 person:1 location:2
    # index one kind of item only
    python manage.py index -i person
    # suppress progressbar
    python manage.py index --no-progress
    # clear everything, then index everything
    python manage.py index --clear all
    # clear and then index one kind of item
    python manage.py index --clear person --index person
    # clear everything, index nothing
    python manage.py index --clear all --index none

"""

import progressbar
import requests
from django.core.management.base import BaseCommand, CommandError
from django.template.defaultfilters import pluralize

from parasolr.django import SolrClient
from parasolr.indexing import Indexable


class Command(BaseCommand):
    """Index content in Solr"""

    help = __doc__

    solr = None

    options = {}
    #: normal verbosity level
    v_normal = 1
    verbosity = v_normal

    indexables = {}

    def init_indexables(self):
        """Find all indexable models and create a dictionary
        keyed on index item type"""
        self.indexables = {
            model.index_item_type(): model for model in Indexable.all_indexables()
        }

    def add_arguments(self, parser):
        self.init_indexables()
        # indexing choices: all, none, and all indexable model names
        choices = ["all"] + list(self.indexables.keys())
        # allow indexing none so you can clear without indexing
        index_choices = choices + ["none"]

        parser.add_argument(
            "index_ids", nargs="*", help="List of specific items to index (optional)"
        )
        parser.add_argument(
            "-i",
            "--index",
            choices=index_choices,
            default="all",
            help="Index all items or one content type (by default indexes all)",
        )
        parser.add_argument(
            "--no-progress",
            action="store_true",
            help="Do not display progress bar to track the status of the reindex.",
        )
        parser.add_argument(
            "-c",
            "--clear",
            choices=choices,
            required=False,
            help="Clear some or all indexed data before reindexing",
        )

    def handle(self, *args, **kwargs):
        self.solr = SolrClient()
        self.verbosity = kwargs.get("verbosity", self.v_normal)
        self.options = kwargs

        # clear index if requested
        if self.options["clear"]:
            self.clear(self.options["clear"])

        total_to_index = 0
        to_index = []

        # index specific items by id
        if self.options["index_ids"]:
            # NOTE: could probably query more efficiently, but this is
            # for manual id entry so should never be very many at once
            for index_id in self.options["index_ids"]:
                # relies on default format of index_id in indexable
                unrecognized_err = "Unrecognized index id '{}'".format(index_id)
                # error if id can not be split
                if Indexable.ID_SEPARATOR not in index_id:
                    raise CommandError(unrecognized_err)

                index_type, item_id = index_id.split(Indexable.ID_SEPARATOR)
                # error if split but index type is not found
                if index_type not in self.indexables:
                    raise CommandError(unrecognized_err)
                to_index.append(self.indexables[index_type].objects.get(pk=item_id))
            total_to_index = len(to_index)

        else:
            # calculate total to index across all indexables for current mode
            for name, model in self.indexables.items():
                if self.options["index"] in [name, "all"]:
                    try:
                        # first, check for model method to provide
                        # efficient count
                        total_to_index += model.total_to_index()
                    except (AttributeError, NotImplementedError):
                        # if count errors because we have a non-model
                        # indexable or a  list, fall back to len
                        # NOTE: this means we generate items to index
                        # unnecessarily without storing the results!
                        total_to_index += len(model.items_to_index())

        # initialize progressbar if requested and indexing more than 5 items
        progbar = None
        if not self.options["no_progress"] and total_to_index > 5:
            progbar = progressbar.ProgressBar(
                redirect_stdout=True, max_value=total_to_index
            )
        count = 0

        # index items requested
        if to_index:
            # list of objects already gathered
            count += self.index(to_index, progbar=progbar)

        else:
            # iterate over indexables by type and index if requested
            for name, model in self.indexables.items():
                if self.options["index"] in [name, "all"]:
                    # index in chunks and update progress bar
                    count += self.index(model.items_to_index(), progbar=progbar)

        if progbar:
            progbar.finish()

        # commit all the indexed changes
        self.solr.update.index([], commit=True)

        # report total items indexed
        if self.verbosity >= self.v_normal:
            # using format for comma-separated numbers
            self.stdout.write("Indexed {:,} item{}".format(count, pluralize(count)))

    def index(self, index_data, progbar=None):
        """Index an iterable into the configured solr"""
        try:
            # index in chunks and update progress bar if there is one
            return Indexable.index_items(index_data, progbar=progbar)
        except requests.exceptions.ConnectionError as err:
            # bail out if we error connecting to Solr
            raise CommandError(err)

    def clear(self, mode):
        """Remove items from the Solr index.  Mode should be 'all" or
        or an item type for a configured indexable."""
        if mode == "all":
            del_query = "*:*"
        else:
            # construct query based on item type
            del_query = "item_type_s:%s" % mode

        if self.verbosity >= self.v_normal:
            # pluralize indexable names but not all
            label = "everything" if mode == "all" else "%s" % mode
            self.stdout.write("Clearing %s from the index" % label)

        # return value doesn't tell us anything useful, so nothing
        # to return here
        self.solr.update.delete_by_query(del_query)
