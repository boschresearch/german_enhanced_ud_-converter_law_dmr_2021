#  Copyright (c) 2021 Robert Bosch GmbH
#  All rights reserved.
#
#  This source code is licensed under the BSD 3-Clause license found in the
#  LICENSE file in the root directory of this source tree.
#
#  Author: Teresa Bürkle

import logging
import math
import argparse

import pyconll
from pyconll.unit.sentence import Sentence


def is_raising_control(sentence):
    """
    Checks whether a sentence contains a raising or control structure by looking for xcomp relations between verbs or
    adjectives
    :param sentence: sentence to check
    :return: True if sentence contains a raising or control structure, False otherwise
    """
    for token in sentence:
        # only returns true if xcomp relation is between verb or adjective tokens
        if token.deprel == 'xcomp' and token.upos in {"VERB", "ADJ", "NOUN"} \
                and sentence[token.head].upos in {"VERB", "ADJ"}:
            logging.debug(f"Sentence {sentence.id} contains a raising / control structure")
            return True
    return False


def is_relative(sentence):
    """
    Checks whether a sentence contains a relative clause by looking for acl:relcl, acl or rel relations
    :param sentence: sentence to check
    :return: True if sentence contains a relative clause, False otherwise
    """
    for token in sentence:
        # relation depends on treebank
        if token.deprel == 'acl:relcl' or token.deprel == 'acl' and sentence[token.head].upos not in {"VERB"}:
            logging.debug(f"Sentence {sentence.id} contains a relative clause")
            return True
    return False


def is_conjunction(sentence):
    """
    Checks whether a sentence contains a coordinate construction by looking for conj relations
    :param sentence: sentence to check
    :return: True if sentence contains a coordinate construction, False otherwise
    """
    for token in sentence:
        if token.deprel == 'conj':
            logging.debug(f"Sentence {sentence.id} contains a conjunction")
            return True
    return False


class Converter:

    def __init__(self, file, use_xsubj):
        logging.basicConfig(level="INFO")
        self.file = file
        self.conll = self.load_conll(file)
        self.token2children = {}
        self.generate_token2children()
        self.use_xsubj = use_xsubj
        print(use_xsubj)

    def convert(self):
        """
        Converts all sentences in the conllu file on which the converter was instantiated by applying rules for each of
        the phenomena conjunction, raising and control and relative clauses. Rules are applied multiple times to treat
        nested phenomena.
        :return: enhanced UD representation of sentences a a string in conllu format
        """
        result_sentences = ''  # result as conll-string
        sentence: Sentence
        # iterate over sentences in file
        for sentence in pyconll.iter_from_file(self.file):
            logging.debug(f"Converting sentence {sentence.id}")
            for token in sentence:
                if "-" not in token.id:  # if token id is not a range
                    # copy basic dependency relations (deprel) to enhanced graph (deps)
                    # noinspection PyTypeChecker
                    sentence[token.id].deps[token.head] = (str(token.deprel), None, None, None)
            # check for phenomena and apply rules if sentence contains phenomenon
            # multiple times to ensure dependent phenomena are treated correctly
            if is_conjunction(sentence):
                sentence = self.apply_conjunction(sentence)
                sentence = self.apply_conjunction(sentence)
            if is_raising_control(sentence):
                sentence = self.apply_raising_control(sentence)
            if is_conjunction(sentence):
                sentence = self.apply_conjunction(sentence)
            if is_relative(sentence):
                sentence = self.apply_relative(sentence)
            if is_conjunction(sentence):
                sentence = self.apply_conjunction(sentence)
                sentence = self.apply_conjunction(sentence)
                sentence = self.apply_conjunction(sentence)
            # add modified sentence to result string
            result_sentences += f'{sentence.conll()}\n\n'
            print(sentence.conll() + "\n")
        return result_sentences

    def generate_token2children(self):
        """
        Iterate over all sentences in the file and create a token2children dictionary for each of them.
        Keys are sentence ids on the first level and token ids on the second level
        :return: dictionary containing child tokens of each token
        """
        # iterate over all sentences to be converted
        for sentence in pyconll.iter_from_file(self.file):
            # create new dict for each sentence
            self.token2children[sentence.id] = dict()
            # create new empty children list for each token except for range id tokens
            for token in sentence:
                if "-" not in token.id:
                    self.token2children[sentence.id][token.id] = []
            # add each token in the sentence to the set of its head node
            for token in sentence:
                if token.head != '0' and token.head is not None:  # except for root token and range id tokens
                    self.token2children[sentence.id][token.head].append(token)

    @staticmethod
    def load_conll(file):
        """
        Loads the Conll object from a file
        :return: a Conll object
        """
        return pyconll.load_from_file(file)

    def apply_conjunction(self, sentence):
        """
        Creates an enhanced UD representation for a given basic UD representation of a given sentence
        regarding conjunctions.
        :return: enhanced UD representation regarding conjunctions of a sentence as a pyconll sentence object
        :type sentence: Sentence
        :param sentence: basic pyconll representation of the sentence to be enhanced
        """
        # iterate over tokens in each sentence
        logging.debug("applying rules for conjunction sentences")
        for token in sentence:
            # find node that has a conj relation to its head
            if token.deprel == "conj":
                conj_child = token  # child node of the conj relation
                conj_head = sentence[conj_child.head]  # head node of the conj relation
                # ====== case 1: conjoined tokens are verbs ===========================================================
                if conj_child.upos == "VERB":
                    logging.debug("Applying rules for conjoined verbs")
                    # propagation of nominal subject
                    # check if token already has a subject, if no, nsubj link is
                    has_subject = False
                    for child in self.token2children[sentence.id][conj_child.id]:
                        logging.debug(f"Checking if {conj_child.form} has a subject relation with {child.form}")
                        if sentence[child.id].deps[conj_child.id][0] in {"nsubj", "nsubj:pass"}:
                            logging.debug(
                                f"Second {conj_child.form} does have a subject ({child.form}), "
                                f"therefore not propagating nsubj link")
                            has_subject = True
                    if not has_subject:
                        # get child of conj head with nsubj relation
                        for conj_head_child in self.token2children[sentence.id][conj_head.id]:
                            logging.debug(f"Conj_head_child is {conj_head_child.id} and conj_head is {conj_head.id}")
                            if "nsubj" in sentence[conj_head_child.id].deps[conj_head.id] or "nsubj:pass" in \
                                    sentence[conj_head_child.id].deps[conj_head.id]:
                                conj_head_nsubj_child = sentence[
                                    conj_head_child.id]  # nsubj of the first conjoined verb
                                # make token subject of the second verb too
                                if conj_head_nsubj_child.deps[conj_head.id][0] not in {"parataxis"}:
                                    # noinspection PyTypeChecker
                                    sentence[conj_head_nsubj_child.id].deps[conj_child.id] = (
                                        conj_head_nsubj_child.deps[conj_head.id][0], None, None, None)
                                    # modify children map accordingly
                                    self.token2children[sentence.id][conj_child.id].append(conj_head_nsubj_child)
                                    logging.debug(
                                        f"New nsubj-child of the conj-head is token \"{conj_head_child.form}\"")
                    # --------------- propagation of objects from the first conjunct (outgoing conj relation) ----------
                    # to the second conjunct (incoming conj relation)
                    conj_head_obj_child = None
                    # find object of the first conjoined verb
                    for child in self.token2children[sentence.id][conj_head.id]:
                        if "obj" in child.deprel:
                            conj_head_obj_child = child
                            logging.debug(f"First conjunct has an object: {conj_head_obj_child.form}")
                    if conj_head_obj_child is not None:
                        # if both conjuncts come before the first conjuncts object in surface order,
                        # propagate obj to second conjunct
                        logging.debug("Checking if first conjunct's object comes after both conjuncts")
                        if (int(conj_child.id) > int(conj_head.id)) and \
                                (int(conj_head_obj_child.id) > int(conj_child.id)):
                            logging.debug("First conjunct's object comes after both conjuncts, "
                                          f"therefore propagating object link.")
                            # noinspection PyTypeChecker
                            sentence[conj_head_obj_child.id].deps[conj_child.id] = ("obj", None, None, None)
                            self.token2children[sentence.id][conj_child.id].append(
                                conj_head_obj_child)  # modify children map
                # ======= case 2: first conjunct has an outgoing and an ingoing conj relation =========================
                elif conj_head.head != '0' and sentence[conj_head.head].head != '0' and conj_head.deprel == 'conj':
                    conj_head_head = sentence[conj_head.head]  # head node of the head node of the conj relation
                    if conj_head_head.deprel != 'conj':
                        # add conj head head as a head of the second conjunct
                        # noinspection PyTypeChecker
                        conj_child.deps[sentence[conj_head_head.id].head] = (
                            conj_head_head.deprel, None, None, None)  # modify enhanced dependencies
                        self.token2children[sentence.id][sentence[conj_head_head.id].head].append(
                            conj_child)  # modify children map
                # ====== case 3: conjunction of tokens that are not verbs and neither of the conjuncts is sentence root
                # ("standard" case)
                elif conj_head.head != '0':
                    # get all heads and respective relations of the first conjunct
                    for conj_head_head_id, conj_head_head_rel in conj_head.deps.items():
                        # head node of the head node of the conj relation
                        if conj_head_head_rel[0] not in {"parataxis", "appos"}:
                            # noinspection PyTypeChecker
                            conj_child.deps[str(conj_head_head_id)] = (
                                conj_head_head_rel[0], None, None,
                                None)  # propagate first conjuncts heads to the second conjunct
                            self.token2children[sentence.id][str(conj_head_head_id)].append(
                                conj_child)  # modify children map
                # ==================== case 4: conj_head is sentence root but not a verb ======================
                else:
                    conj_head_children = self.token2children[sentence.id][conj_head.id]
                    for child in conj_head_children:
                        if child.deprel in {'nsubj', 'aux', 'xcomp', 'acl'}:
                            logging.debug(f"Found child [{child.id}] {child.form} with relation {child.deprel}")
                            # make conj child an additional head of the child
                            # noinspection PyTypeChecker
                            sentence[child.id].deps[
                                conj_child.id] = (
                                str(child.deprel), None, None, None)
                            self.token2children[sentence.id][conj_child.id].append(child)
        return sentence

    def apply_relative(self, sentence):
        """
        Creates an enhanced UD representation for a given basic UD representation of a given sentence
        regarding relative clauses. Rules applied depend on whether relative clause has a possessive pronoun
        functioning as a relative pronoun or not
        :return: enhanced UD representation of a sentence as a pyconll sentence object regarding relative clauses
        :param sentence: basic pyconll representation of the sentence to be enhanced
        :type sentence: Sentence
        """
        logging.debug(f"Applying rules for relative sentences for sentence {sentence.id}")
        # get acl_child and antecedent
        for token in sentence:
            # get head and child node of the rel relation (relation type depending on treebank)
            if token.deprel == 'acl:relcl' or token.deprel == 'acl':
                acl_child = token  # incoming rel relation
                antecedent = sentence[token.head]  # outgoing rel relation
                logging.debug(
                    f"Identified rel relation from token antecedent [{antecedent.id}] {antecedent.form} to token "
                    f"acl_child [{acl_child.id}] {acl_child.form}")
                # get relativizer, which is the first surface order child of the token with
                # an incoming acl relation governed by anything but a punct relation
                lowest_id = math.inf
                for child in self.token2children[sentence.id][acl_child.id]:
                    if int(child.id) < lowest_id and child.deprel != "punct":
                        logging.debug(f"lowest ID is currently {lowest_id} for child {child.id} {child.form}")
                        lowest_id = int(child.id)
                relativizer = None if lowest_id == math.inf else sentence[str(lowest_id)]
                logging.debug(f"rel del child is {relativizer}")
                # ----- relative clause where relativizer / relative pronoun functions as possessive pronoun
                # if token at the position of the relative pronoun is a noun
                if relativizer is not None and relativizer.upos == 'NOUN':
                    possessed_noun = relativizer
                    logging.debug(f"Rel del child {possessed_noun.form} is a noun")
                    possessive_relativizer = None
                    # get the possessive pronoun referring semantically to the antecedent
                    for possessed_noun_child in self.token2children[sentence.id][possessed_noun.id]:
                        # always "deren" or "dessen" in german
                        if possessed_noun_child.form == "deren" or possessed_noun_child.form == "dessen":
                            possessive_relativizer = possessed_noun_child
                        if possessive_relativizer is not None:  # add relations
                            logging.debug(
                                f"Poss rel del child is token {possessive_relativizer.id}")
                            sentence[possessive_relativizer.id].deps.clear()
                            # noinspection PyAssignmentToLoopOrWithParameter
                            for token in sentence:
                                if "-" not in token.id:
                                    for token_child in self.token2children[sentence.id][token.id]:
                                        logging.debug(f"Checking token child {token_child.form} for token {token.form}")
                                        if token_child == possessive_relativizer:
                                            self.token2children[sentence.id][token.id].remove(possessive_relativizer)
                            # make reference from token with outgoing acl relation to possessive pronoun
                            # noinspection PyTypeChecker
                            sentence[possessive_relativizer.id].deps[antecedent.id] = ('ref', None, None, None)
                            self.token2children[sentence.id][antecedent.id].append(
                                possessive_relativizer)  # modify children
                            # propagate possessing relation from possessive pronouns possessor to token with outgoing
                            # acl relation
                            # noinspection PyTypeChecker
                            sentence[antecedent.id].deps[possessed_noun.id] = ("nmod:poss", None, None, None)
                            self.token2children[sentence.id][possessed_noun.id].append(
                                antecedent)  # modify children map
                            logging.debug(
                                f"adding ref relation from token {antecedent.id} {antecedent.form} "
                                f"to possessive_relativizer")
                            break
                # ------- regular relative clause (no possessive relative pronoun) ----------------------------
                elif relativizer is not None and (
                        relativizer.upos == "PRON" or relativizer.lemma == "wo") and relativizer.xpos != "PRF":
                    logging.debug(f"Rel_del_child is token [{relativizer.id}] {relativizer.form}")
                    # propagate incoming relation of the relative pronoun or relativizer from token with incoming
                    # rel relation to token with outgoing rel relation
                    for relation_head in relativizer.deps:
                        if relation_head[0] != "ref":
                            # noinspection PyTypeChecker
                            sentence[antecedent.id].deps[relation_head] = (
                                str(relativizer.deps[relation_head][0]), None, None, None)
                            self.token2children[sentence.id][relation_head].append(antecedent)  # modify children map
                            for relation_head_child in self.token2children[sentence.id][relation_head]:
                                if relation_head_child.id == relativizer.id:
                                    self.token2children[sentence.id][relation_head].remove(relation_head_child)
                    sentence[relativizer.id].deps.clear()  # delete enhanced relation
                    # noinspection PyAssignmentToLoopOrWithParameter
                    for token in sentence:
                        if "-" not in token.id:
                            for token_child in self.token2children[sentence.id][token.id]:
                                logging.debug(f"Checking token child {token_child.form} for token {token.form}")
                                if token_child == relativizer:
                                    self.token2children[sentence.id][token.id].remove(relativizer)
                    # add ref relation from antecedent to relative pronoun or relativizer
                    # noinspection PyTypeChecker
                    sentence[relativizer.id].deps[antecedent.id] = ('ref', None, None, None)
                    self.token2children[sentence.id][antecedent.id].append(relativizer)
        return sentence

    def apply_raising_control(self, sentence):
        """
                Creates an enhanced UD representation for a given basic UD representation of a given sentence regarding
                raising and control structures
                :return: enhanced UD representation of a sentence as a pyconll sentence object
                regarding raising and control structures
                :param sentence: basic pyconll representation of the sentence to be enhanced
                :type sentence: Sentence
                """
        logging.debug("applying rules for raising control")
        for token in sentence:
            should_continue = False
            if token.deprel == "xcomp":
                xcomp_child = token
                xcomp_head = sentence[xcomp_child.head]
                if xcomp_head.lemma == "lassen":  # don't propagate anything if xcomp head is "lassen"
                    return sentence
                # --- case 1: xcomp head has an indirect object -----------------------------------------
                for xcomp_head_child in self.token2children[sentence.id][xcomp_head.id]:
                    if xcomp_head_child.deprel == 'iobj' and xcomp_head_child.xpos not in {"PRF", "PRP"}:
                        # make indirect object the xcomp child's nominal subject
                        # noinspection PyTypeChecker
                        sentence[xcomp_head_child.id].deps[xcomp_child.id] = ('nsubj:xsubj', None, None, None) \
                                                                    if self.use_xsubj else ('nsubj', None, None, None)
                        self.token2children[sentence.id][xcomp_child.id].append(xcomp_head_child)  # modify children map
                        logging.debug(
                            f"xcomp head {xcomp_head.id} has iobj child to {xcomp_head_child.id}, adding "
                            f"nsubj from {xcomp_child.id} to {xcomp_head_child.id}")
                        should_continue = True
                if should_continue:
                    continue
                # --- case 2: xcomp head has no indirect, but a direct object ------------------------------------------
                for xcomp_head_child in self.token2children[sentence.id][xcomp_head.id]:
                    if xcomp_head_child.deprel == 'obj' and xcomp_head_child.xpos not in {"PRF", "PRP"}:
                        # make direct object the xcomp child's nominal subject
                        # noinspection PyTypeChecker
                        sentence[xcomp_head_child.id].deps[xcomp_child.id] = ('nsubj:xsubj', None, None, None) \
                                                                    if self.use_xsubj else ('nsubj', None, None, None)
                        self.token2children[sentence.id][xcomp_child.id].append(xcomp_head_child)  # modify children map
                        logging.debug(
                            f"xcomp head {xcomp_head.id} has obj child to {xcomp_head_child.id}, adding "
                            f"nsubj from {xcomp_child.id} to {xcomp_head_child.id}")
                        should_continue = True
                if should_continue:
                    continue
                # --- case 3: xcomp head has no objects, but a subject -------------------------------------------------
                for xcomp_head_child in self.token2children[sentence.id][xcomp_head.id]:
                    if sentence[xcomp_head_child.id].deps[xcomp_head.id][0] == 'nsubj':
                        # make nominal subject the xcomp child's nominal subject
                        # noinspection PyTypeChecker
                        sentence[xcomp_head_child.id].deps[xcomp_child.id] = ('nsubj:xsubj', None, None, None) \
                                                                    if self.use_xsubj else ('nsubj', None, None, None)
                        self.token2children[sentence.id][xcomp_child.id].append(xcomp_head_child)  # modify children map
                        logging.debug(
                            f"xcomp head {xcomp_head.id} has nsubj child "
                            f"to {xcomp_head_child.id}, adding nsubj from {xcomp_child.id} to {xcomp_head_child.id}")
        return sentence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Converter from basic to enhanced universal dependencies for '
                                                 'German texts')
    parser.add_argument('basic_filename', type=str, help='path to conllu-file containing basic annotations (required)')
    parser.add_argument('enhanced_filename', type=str, help='path to output file (required)')
    parser.add_argument('--use_xsubj', default=False, dest='use_xsubj', action='store_true',
                        help='Option to use the nsubj:xsubj subtype when adding nsubj links in raising / control '
                             'constructions instead of the general nsubj relation type (default = false)')
    args = parser.parse_args()

    converter = Converter(args.basic_filename, args.use_xsubj)
    enhanced_file = open(args.enhanced_filename, 'w', encoding='utf-8')
    enhanced_file.write(converter.convert())
    enhanced_file.close()
