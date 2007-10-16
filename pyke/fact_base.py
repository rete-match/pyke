# $Id$
# coding=utf-8
# 
# Copyright © 2007 Bruce Frederiksen
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

'''
    A fact_base is one of the kinds of knowledge_bases (see also, rule_base
    and special).

        >>> fb = fact_base('fb_name')
        >>> fb
        <fact_base fb_name>
        >>> fb.dump_universal_facts()
        >>> fb.dump_specific_facts()

    A fact_base is nothing more than a list of facts.  Each fact has a name
    and a tuple of arguments.  These arguments are python data (not
    patterns).

    Fact_bases support two kinds of facts: universal facts (universally
    true) and case specific facts (only true in a specific situation).

        >>> fb.add_universal_fact('some_universal_fact', ('a', 2))
        >>> fb.add_case_specific_fact('some_specific_fact', ('b', ('hi', 32)))
        >>> fb.dump_universal_facts()
        some_universal_fact('a', 2)
        >>> fb.dump_specific_facts()
        some_specific_fact('b', ('hi', 32))

    The 'reset' method deletes all case specific facts, but leaves the
    universal facts.

        >>> fb.reset()
        >>> fb.dump_universal_facts()
        some_universal_fact('a', 2)
        >>> fb.dump_specific_facts()

    Normally, universal facts are established once at program
    initialization time and case specific facts are established both just
    prior to each invocation of the expert system as well as by assertions
    in forward chaining rules.

        >>> fb.assert_('some_fact', ('a', 2, ('hi', 'mom')))
        >>> fb.dump_universal_facts()
        some_universal_fact('a', 2)
        >>> fb.dump_specific_facts()
        some_fact('a', 2, ('hi', 'mom'))
        >>> fb.assert_('some_fact', ('a', 3, ('hi', 'mom')))
        >>> fb.dump_specific_facts()
        some_fact('a', 2, ('hi', 'mom'))
        some_fact('a', 3, ('hi', 'mom'))
        >>> fb.assert_('some_other_fact', ())
        >>> fb.dump_specific_facts()
        some_fact('a', 2, ('hi', 'mom'))
        some_fact('a', 3, ('hi', 'mom'))
        some_other_fact()
    
    Duplicate facts are not allowed and trying to assert a duplicate fact is
    silently ignored.

        >>> fb.assert_('some_fact', ('a', 2, ('hi', 'mom')))
        >>> fb.dump_specific_facts()
        some_fact('a', 2, ('hi', 'mom'))
        some_fact('a', 3, ('hi', 'mom'))
        some_other_fact()

'''

from __future__ import with_statement, absolute_import, division
from pyke import tmp_itertools as itertools
from pyke import knowledge_base, contexts

class fact_base(knowledge_base.knowledge_base):
    ''' Not much to fact_bases.  The real work is done in fact_list! '''
    def __init__(self, name):
	super(fact_base, self).__init__(name, fact_list)
    def dump_universal_facts(self):
	for fl_name in sorted(self.entity_lists.iterkeys()):
            self.entity_lists[fl_name].dump_universal_facts()
    def dump_specific_facts(self):
	for fl_name in sorted(self.entity_lists.iterkeys()):
            self.entity_lists[fl_name].dump_specific_facts()
    def add_universal_fact(self, fact_name, args):
	self.get_entity_list(fact_name).add_universal_fact(args)
    def add_case_specific_fact(self, fact_name, args):
	self.get_entity_list(fact_name).add_case_specific_fact(args)
    def assert_(self, fact_name, args):
	self.add_case_specific_fact(fact_name, args)

class fact_list(knowledge_base.knowledge_entity_list):
    def __init__(self, name):
        super(fact_list, self).__init__(name)
	self.universal_facts = set()		# (arg...)
	self.case_specific_facts = set()	# (arg...)
	self.hashes = {}	# (len, (index...)): (other_indices,
				#	{(arg...): [other_args_from_factn...]})
	self.fc_rule_refs = []	# (fc_rule, foreach_index)
    def reset(self):
	self.case_specific_facts.clear()
	self.hashes.clear()
	self.fc_rule_refs = []
    def dump_universal_facts(self):
	for args in self.universal_facts:
	    print '%s%s' % (self.name, args)
    def dump_specific_facts(self):
	for args in self.case_specific_facts:
	    print '%s%s' % (self.name, args)
    def add_fc_rule_ref(self, fc_rule, foreach_index):
	self.fc_rule_refs.append((fc_rule, foreach_index))
    def get_affected_fc_rules(self):
	return (fc_rule for fc_rule, foreach_index in self.fc_rule_refs)
    def lookup(self, bindings, pat_context, patterns):
	""" Binds patterns to successive facts, yielding None for each
	    successful match.  Undoes bindings upon continuation, so that no
	    bindings remain at StopIteration.
	"""
	indices = tuple(enum for enum in enumerate(patterns)
			     if enum[1].is_data(pat_context))
	other_indices, other_arg_lists = \
	    self._get_hashed(len(patterns),
			     tuple(index[0] for index in indices),
			     tuple(index[1].as_data(pat_context)
				   for index in indices))
	if other_arg_lists:
	    for args in other_arg_lists:
                mark = bindings.mark(True)
		if all(itertools.imap(lambda i, arg:
					  patterns[i].match_data(bindings,
								 pat_context,
								 arg),
				      other_indices,
				      args)):
                    bindings.end_save_all_undo()
		    yield
                else:
                    bindings.end_save_all_undo()
		bindings.undo_to_mark(mark)
    def _get_hashed(self, len, indices, args):
	ans = self.hashes.get((len, indices))
	if ans is None: ans = self._hash(len, indices)
	other_indices, arg_map = ans
	return other_indices, arg_map.get(args, ())
    def _hash(self, length, indices):
	args_hash = {}
	new_entry = (tuple(i for i in range(length) if i not in indices),
		     args_hash)
	self.hashes[length, indices] = new_entry
	for args in itertools.chain((self.universal_facts,
				     self.case_specific_facts)):
	    if len(args) == length:
		selected_args = tuple(arg for i, arg in enumerate(args)
					  if i in indices)
		args_hash.setdefault(selected_args, []) \
			 .append(tuple(arg for i, arg in enumerate(args)
					   if i not in indices))
	return new_entry
    def add_universal_fact(self, args):
	if args not in self.universal_facts:
	    self.universal_facts.add(args)
	    self.add_args(args)
    def add_case_specific_fact(self, args):
	if args not in self.case_specific_facts:
	    self.case_specific_facts.add(args)
	    self.add_args(args)
	    for fc_rule, foreach_index in self.fc_rule_refs:
		fc_rule.new_fact(args, foreach_index)
    def add_args(self, args):
	for (length, indices), (other_indices, arg_map) \
	 in self.hashes.iteritems():
	    if length == len(args):
		selected_args = tuple(arg for i, arg in enumerate(args)
					  if i in indices)
		arg_map.setdefault(selected_args, []) \
		       .append(tuple(arg for i, arg in enumerate(args)
					 if i not in indices))

def test():
    import doctest
    import sys
    sys.exit(doctest.testmod()[0])

if __name__ == "__main__":
    test()