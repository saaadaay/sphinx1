"""
    sphinx.domains.c
    ~~~~~~~~~~~~~~~~

    The C language domain.

    :copyright: Copyright 2007-2020 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import string
from typing import Any, Dict, Iterator, List, Tuple
from typing import cast

from docutils import nodes
from docutils.nodes import Element

from sphinx import addnodes
from sphinx.addnodes import pending_xref, desc_signature
from sphinx.application import Sphinx
from sphinx.builders import Builder
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.environment import BuildEnvironment
from sphinx.locale import _, __
from sphinx.roles import XRefRole
from sphinx.util import logging
from sphinx.util.docfields import Field, TypedField
from sphinx.util.nodes import make_refnode


logger = logging.getLogger(__name__)

# RE to split at word boundaries
wsplit_re = re.compile(r'(\W+)')

# REs for C signatures
c_sig_re = re.compile(
    r'''^([^(]*?)          # return type
        ([\w:.]+)  \s*     # thing name (colon allowed for C++)
        (?: \((.*)\) )?    # optionally arguments
        (\s+const)? $      # const specifier
    ''', re.VERBOSE)
c_funcptr_sig_re = re.compile(
    r'''^([^(]+?)          # return type
        (\( [^()]+ \)) \s* # name in parentheses
        \( (.*) \)         # arguments
        (\s+const)? $      # const specifier
    ''', re.VERBOSE)
c_funcptr_arg_sig_re = re.compile(
    r'''^\s*([^(,]+?)      # return type
        \( ([^()]+) \) \s* # name in parentheses
        \( (.*) \)         # arguments
        (\s+const)?        # const specifier
        \s*(?=$|,)         # end with comma or end of string
    ''', re.VERBOSE)
c_funcptr_name_re = re.compile(r'^\(\s*\*\s*(.*?)\s*\)$')


class CObject(ObjectDescription):
    """
    Description of a C language object.
    """

    doc_field_types = [
        TypedField('parameter', label=_('Parameters'),
                   names=('param', 'parameter', 'arg', 'argument'),
                   typerolename='type', typenames=('type',)),
        Field('returnvalue', label=_('Returns'), has_arg=False,
              names=('returns', 'return')),
        Field('returntype', label=_('Return type'), has_arg=False,
              names=('rtype',)),
    ]

    # These C types aren't described anywhere, so don't try to create
    # a cross-reference to them
    stopwords = {
        'const', 'void', 'char', 'wchar_t', 'int', 'short',
        'long', 'float', 'double', 'unsigned', 'signed', 'FILE',
        'clock_t', 'time_t', 'ptrdiff_t', 'size_t', 'ssize_t',
        'struct', '_Bool',
    }

    def _parse_type(self, node: Element, ctype: str) -> None:
        # add cross-ref nodes for all words
        for part in [_f for _f in wsplit_re.split(ctype) if _f]:
            tnode = nodes.Text(part, part)
            if part[0] in string.ascii_letters + '_' and \
               part not in self.stopwords:
                pnode = pending_xref('', refdomain='c', reftype='type', reftarget=part,
                                     modname=None, classname=None)
                pnode += tnode
                node += pnode
            else:
                node += tnode

    def _parse_arglist(self, arglist: str) -> Iterator[str]:
        while True:
            m = c_funcptr_arg_sig_re.match(arglist)
            if m:
                yield m.group()
                arglist = c_funcptr_arg_sig_re.sub('', arglist)
                if ',' in arglist:
                    _, arglist = arglist.split(',', 1)
                else:
                    break
            else:
                if ',' in arglist:
                    arg, arglist = arglist.split(',', 1)
                    yield arg
                else:
                    yield arglist
                    break

    def handle_signature(self, sig: str, signode: desc_signature) -> str:
        """Transform a C signature into RST nodes."""
        # first try the function pointer signature regex, it's more specific
        m = c_funcptr_sig_re.match(sig)
        if m is None:
            m = c_sig_re.match(sig)
        if m is None:
            raise ValueError('no match')
        rettype, name, arglist, const = m.groups()

        desc_type = addnodes.desc_type('', '')
        signode += desc_type
        self._parse_type(desc_type, rettype)
        try:
            classname, funcname = name.split('::', 1)
            classname += '::'
            signode += addnodes.desc_addname(classname, classname)
            signode += addnodes.desc_name(funcname, funcname)
            # name (the full name) is still both parts
        except ValueError:
            signode += addnodes.desc_name(name, name)
        # clean up parentheses from canonical name
        m = c_funcptr_name_re.match(name)
        if m:
            name = m.group(1)

        typename = self.env.ref_context.get('c:type')
        if self.name == 'c:member' and typename:
            fullname = typename + '.' + name
        else:
            fullname = name

        if not arglist:
            if self.objtype == 'function' or \
                    self.objtype == 'macro' and sig.rstrip().endswith('()'):
                # for functions, add an empty parameter list
                signode += addnodes.desc_parameterlist()
            if const:
                signode += addnodes.desc_addname(const, const)
            return fullname

        paramlist = addnodes.desc_parameterlist()
        arglist = arglist.replace('`', '').replace('\\ ', '')  # remove markup
        # this messes up function pointer types, but not too badly ;)
        for arg in self._parse_arglist(arglist):
            arg = arg.strip()
            param = addnodes.desc_parameter('', '', noemph=True)
            try:
                m = c_funcptr_arg_sig_re.match(arg)
                if m:
                    self._parse_type(param, m.group(1) + '(')
                    param += nodes.emphasis(m.group(2), m.group(2))
                    self._parse_type(param, ')(' + m.group(3) + ')')
                    if m.group(4):
                        param += addnodes.desc_addname(m.group(4), m.group(4))
                else:
                    ctype, argname = arg.rsplit(' ', 1)
                    self._parse_type(param, ctype)
                    # separate by non-breaking space in the output
                    param += nodes.emphasis(' ' + argname, '\xa0' + argname)
            except ValueError:
                # no argument name given, only the type
                self._parse_type(param, arg)
            paramlist += param
        signode += paramlist
        if const:
            signode += addnodes.desc_addname(const, const)
        return fullname

    def get_index_text(self, name: str) -> str:
        if self.objtype == 'function':
            return _('%s (C function)') % name
        elif self.objtype == 'member':
            return _('%s (C member)') % name
        elif self.objtype == 'macro':
            return _('%s (C macro)') % name
        elif self.objtype == 'type':
            return _('%s (C type)') % name
        elif self.objtype == 'var':
            return _('%s (C variable)') % name
        else:
            return ''

    def add_target_and_index(self, name: str, sig: str, signode: desc_signature) -> None:
        # for C API items we add a prefix since names are usually not qualified
        # by a module name and so easily clash with e.g. section titles
        targetname = 'c.' + name
        if targetname not in self.state.document.ids:
            signode['names'].append(targetname)
            signode['ids'].append(targetname)
            self.state.document.note_explicit_target(signode)

            domain = cast(CDomain, self.env.get_domain('c'))
            domain.note_object(name, self.objtype)

        indextext = self.get_index_text(name)
        if indextext:
            self.indexnode['entries'].append(('single', indextext,
                                              targetname, '', None))

    def before_content(self) -> None:
        self.typename_set = False
        if self.name == 'c:type':
            if self.names:
                self.env.ref_context['c:type'] = self.names[0]
                self.typename_set = True

    def after_content(self) -> None:
        if self.typename_set:
            self.env.ref_context.pop('c:type', None)


class CXRefRole(XRefRole):
    def process_link(self, env: BuildEnvironment, refnode: Element,
                     has_explicit_title: bool, title: str, target: str) -> Tuple[str, str]:
        if not has_explicit_title:
            target = target.lstrip('~')  # only has a meaning for the title
            # if the first character is a tilde, don't display the module/class
            # parts of the contents
            if title[0:1] == '~':
                title = title[1:]
                dot = title.rfind('.')
                if dot != -1:
                    title = title[dot + 1:]
        return title, target


class CDomain(Domain):
    """C language domain."""
    name = 'c'
    label = 'C'
    object_types = {
        'function': ObjType(_('function'), 'func'),
        'member':   ObjType(_('member'),   'member'),
        'macro':    ObjType(_('macro'),    'macro'),
        'type':     ObjType(_('type'),     'type'),
        'var':      ObjType(_('variable'), 'data'),
    }

    directives = {
        'function': CObject,
        'member':   CObject,
        'macro':    CObject,
        'type':     CObject,
        'var':      CObject,
    }
    roles = {
        'func':   CXRefRole(fix_parens=True),
        'member': CXRefRole(),
        'macro':  CXRefRole(),
        'data':   CXRefRole(),
        'type':   CXRefRole(),
    }
    initial_data = {
        'objects': {},  # fullname -> docname, objtype
    }  # type: Dict[str, Dict[str, Tuple[str, Any]]]

    @property
    def objects(self) -> Dict[Tuple[str, str], str]:
        return self.data.setdefault('objects', {})  # objtype, fullname -> docname

    def note_object(self, name: str, objtype: str, location: Any = None) -> None:
        if (objtype, name) in self.objects:
            docname = self.objects[objtype, name]
            logger.warning(__('duplicate C object description of %s, '
                              'other instance in %s, use :noindex: for one of them'),
                           name, docname, location=location)
        self.objects[objtype, name] = self.env.docname

    def clear_doc(self, docname: str) -> None:
        for key, fn in list(self.objects.items()):
            if fn == docname:
                del self.objects[key]

    def merge_domaindata(self, docnames: List[str], otherdata: Dict) -> None:
        # XXX check duplicates
        for key, fn in otherdata['objects'].items():
            if fn in docnames:
                self.objects[key] = fn

    def resolve_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                     typ: str, target: str, node: pending_xref, contnode: Element
                     ) -> Element:
        objtypes = self.objtypes_for_role(typ)
        # strip pointer asterisk
        target = target.rstrip(' *')
        # becase TypedField can generate xrefs
        if target in CObject.stopwords:
            return contnode
        for objtype in objtypes:
            if (objtype, target) in self.objects:
                docname = self.objects[objtype, target]
                return make_refnode(builder, fromdocname, docname, 'c.' + target,
                                    contnode, target)

        return None

    def resolve_any_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                         target: str, node: pending_xref, contnode: Element
                         ) -> List[Tuple[str, Element]]:
        # strip pointer asterisk
        target = target.rstrip(' *')

        results = []  # type: List[Tuple[str, Element]]
        for (objtype, objname), docname in self.objects.items():
            if target == objname:
                role = 'c:' + self.role_for_objtype(objtype)
                refnode = make_refnode(builder, fromdocname, docname, 'c.' + target,
                                       contnode, target)
                results.append((role, refnode))

        return results

    def get_objects(self) -> Iterator[Tuple[str, str, str, str, str, int]]:
        for (objtype, objname), docname in list(self.objects.items()):
            yield (objname, objname, objtype, docname, 'c.' + objname, 1)


def setup(app: Sphinx) -> Dict[str, Any]:
    app.add_domain(CDomain)

    return {
        'version': 'builtin',
        'env_version': 2,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
