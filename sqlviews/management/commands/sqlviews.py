# Copyright (c) 2009 Dennis Kaarsemaker <dennis@kaarsemaker.net>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
#     1. Redistributions of source code must retain the above copyright notice, 
#        this list of conditions and the following disclaimer.
#     
#     2. Redistributions in binary form must reproduce the above copyright 
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
# 
#     3. Neither the name of Django nor the names of its contributors may be used
#        to endorse or promote products derived from this software without
#        specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from django import get_version
from django.core.management.base import AppCommand
from django.conf import settings
from django.db import connection, models
import re
import sys

# Since this thing relies on django internals that are not guaranteed to be stable,
# do a strict version check.
COMPAT_MIN = '1.0'
COMPAT_MAX = '1.3.9999'

def sql_create_views(app, style):
    """Create views for all multi-table models in app"""

    if settings.DATABASE_ENGINE == 'dummy':
        # This must be the "dummy" database backend, which means the user
        # hasn't set DATABASE_ENGINE.
        raise CommandError("Django doesn't know which syntax to use for your SQL statements,\n" +
            "because you haven't specified the DATABASE_ENGINE setting.\n" +
            "Edit your settings file and change DATABASE_ENGINE to something like 'postgresql' or 'mysql'.")

    app_models = models.get_models(app)
    final_output = []

    for model in app_models:
        if not model._meta.parents:
            continue # Not a multi-table-inheritance class
        final_output.append(sql_create_model_view(connection.creation, model, style))
    return final_output

def sql_create_model_view(self, model, style):
    """Create a view for a model. 'self' is the DatabaseCreation instance"""
    qn = self.connection.ops.quote_name
    view = style.SQL_KEYWORD('CREATE VIEW') + ' ' + \
           style.SQL_TABLE(qn(model._meta.db_table + '_view')) + ' ' + \
           style.SQL_KEYWORD('AS') + '\n' + style.SQL_KEYWORD('SELECT') + '\n'

    fields_seen = []
    def hl(m,filter=True):
        table = style.SQL_TABLE(qn(m.group(1)))
        field = m.group(2)
        if field:
            if filter and (field in fields_seen or field.endswith('_ptr_id')):
                return ''
            fields_seen.append(field)
            table += '.' + qn(style.SQL_FIELD(field))
        if filter:
            return '    %s,\n' % table
        return table

    # Use the query internals to create the SELECT query
    # Since that outputs quoted text, unquote it and mangle formatting
    # Slightly hackish but works
    query = model.objects.order_by().query
    print query, type(query)
    if hasattr(query, 'get_compiler'):
        query = query.get_compiler(connection=connection)
    query.pre_sql_setup()
    for col in query.get_columns():
        view += re.sub(r'%s\.%s' % (qn(r'(\S+?)'), qn(r'(\S+?)')), hl, col)

    view = view[:-2] + '\n' + style.SQL_KEYWORD('FROM')
    for clause in query.get_from_clause()[0]:
        clause = ' ' + re.sub(r'%s(?:\.%s)?' % (qn(r'(\S+?)'), qn(r'(\S+?)')), lambda m: hl(m, False), clause) + '\n'
        clause = clause.replace(' ON ', ' ' + style.SQL_KEYWORD('ON') + ' ')
        clause = clause.replace(' INNER JOIN ', '    ' + style.SQL_KEYWORD('INNER JOIN') + ' ')
        view += clause
    return view[:-1] + ';'

class Command(AppCommand):
    help = "Print CREATE VIEW statements for multi-table inheritance models"

    output_transaction = True

    def handle_app(self, app, **options):
        # Since this thing relies on django internals that are not guaranteed to be stable,
        # do a strict version check.
        version = get_version()
        if version < COMPAT_MIN or version > COMPAT_MAX:
            print "This command is not compatible with django version %s" % version
            sys.exit(1)
        return ('\n%s\n' % u'\n'.join(sql_create_views(app, self.style))).encode('utf-8')
