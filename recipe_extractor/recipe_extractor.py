
__author__ = "Olga Kononova"
__maintainer__ = "Olga Kononova"
__email__ = "0lgaGkononova@yandex.ru"
__version__ = "3.0"

import itertools
import re
from pprint import pprint
import collections

import sympy
from sympy.abc import _clash
from chemdataextractor.doc import Paragraph

#from text_cleanup import TextCleanUp
from material_parser.material_parser import MaterialParser
from materials_entity_recognition import MatRecognition

class RecipeExtractor:
    def __init__(self, verbose=False, pubchem_lookup=False, parse_dependency=False):
        print('RecipeExtractor version 3.3')
        #self.__tp = TextCleanUp()
        if parse_dependency:
            print ('Using dependency parse tree for MER.')
        self.__mer = MatRecognition(parse_dependency=parse_dependency)
        self.__mp = MaterialParser(pubchem_lookup=pubchem_lookup)
        #self.__chemical_names = self.__mp.build_names_dictionary()
        self.__verbose = verbose
        self.__pubchem = pubchem_lookup

        self.__greek_letters = [chr(i) for i in range(945, 970)]

        self.__list_of_elements_1 = ['H', 'B', 'C', 'N', 'O', 'F', 'P', 'S', 'K', 'V', 'Y', 'I', 'W', 'U']
        self.__list_of_elements_2 = ['He', 'Li', 'Be', 'Ne', 'Na', 'Mg', 'Al', 'Si', 'Cl', 'Ar', 'Ca', 'Sc', 'Ti', 'Cr',
                                     'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr',
                                     'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'Xe',
                                     'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er',
                                     'Tm', 'Yb', 'Lu', 'Hf', 'Ta', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi',
                                     'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf',
                                     'Es', 'Fm', 'Md', 'No', 'Lr', 'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn',
                                     'Fl', 'Lv']

    def get_materials(self, doi, abstract, syn_paragraph):

        # Text preprocessing: cleaning up paragraphs
        # abstract = self.__tp.cleanup_text(abstract_)
        # syn_paragraph = self.__tp.cleanup_text(syn_paragraph_)

        if self.__verbose:
            print('Abstract:', abstract)
            print('Synthesis paragraph:', syn_paragraph)

        #MER
        abstract_all, abstract_precursors, abstract_targets, abstract_others = self.__mer.mat_recognize(abstract)
        syn_all, syn_precursors, syn_targets, syn_others = self.__mer.mat_recognize(syn_paragraph)

        abstract_materials = dict(
            targets = abstract_targets,
            precursors = abstract_precursors,
            others = abstract_others
        )

        synthesis_materials = dict(
            targets = syn_targets,
            precursors = syn_precursors,
            others = syn_others
        )

        return abstract_materials, synthesis_materials


    def get_composition(self, doi, abstract, syn_paragraph, abstract_materials, synthesis_materials):

        data_structure = {}

        fails = {'targets': [],
                 'precursors':[],
                 'abstracts': [],
                 'others': []}

        abstract_materials = list(set([m for _ in abstract_materials.values() for m in _]))
        #abstract_materials = list(set([m for m in abstract_materials['targets']]))
        targets = list(set([m for m in synthesis_materials['targets']]))
        precursors = list(set([m for m in synthesis_materials['precursors']]))
        others = list(set([m for m in synthesis_materials['others'] if m not in precursors+targets]))

        if self.__verbose:
            print('MER found materials')
            print('\tfrom abstract:', abstract_materials)
            print('\ttargets from synthesis paragaph', targets)
            print('\tprecursors from synthesis paragaph', precursors)


        # Getting dopants
        def extracting_dopants(materials_list=[]):
            materials_list_upd = []
            dopants_list = []
            for material in materials_list:
                dopants, new_name = self.__mp.get_dopants(material)

                dopants_list.extend(d for d in dopants)
                materials_list_upd.append(new_name)

            return list(set(materials_list_upd)), set(dopants_list)

        abstract_materials_upd_1, abstract_dopants = extracting_dopants(abstract_materials)
        targets_upd_1, targets_dopants = extracting_dopants(targets)
        others_upd_1, _ = extracting_dopants(others)

        data_structure['dopants'] = list(targets_dopants.union(abstract_dopants))

        if self.__verbose:
            print('Removed doped parts:')
            print('\tdopants:', data_structure['dopants'])
            print('\tabstract materials', abstract_materials_upd_1)
            print('\ttargets', targets_upd_1)

        # Building abbreviations dictionary
        materials = list(set(abstract_materials_upd_1+targets_upd_1))
        abbreviations = self.__mp.build_abbreviations_dict(materials, [abstract, syn_paragraph])

        if self.__verbose:
            print('Abbreviations dictionary:')
            pprint(abbreviations)

        def substitute_abbreviations(materials_list = [], abbreviations_dict = {}):
            materials_list_upd = []
            for material in materials_list:
                if material in abbreviations_dict:
                    materials_list_upd.append(abbreviations_dict[material])
                else:
                    materials_list_upd.append(material)

            return list(set(materials_list_upd))

        abstract_materials_upd_2 = substitute_abbreviations(abstract_materials_upd_1, abbreviations)
        targets_upd_2 = substitute_abbreviations(targets_upd_1, abbreviations)
        others_upd_2 = substitute_abbreviations(others_upd_1, abbreviations)

        if self.__verbose:
            print('After abbreviations substitution:')
            print('\tabstract:', abstract_materials_upd_2)
            print('\ttargets:', targets_upd_2)

        # Checking for valency
        valency = ''
        for material in abstract_materials_upd_2+targets_upd_2:
            v = re.findall('\s*\(([IV,]+)\)', material)
            if len(v) > 0:
                valency = v[0]

        # Cleaning up materials names
        def cleaning_names(materials_list=[]):
            materials_list_upd = []
            for material in materials_list:
                new_name = self.__mp.clean_up_material_name(material, remove_offstoichiometry=True)
                new_name = self.__mp.split_material_name(new_name)
                if new_name != '':
                    materials_list_upd.append(new_name)
                else:
                    materials_list_upd.append(material)
            return list(set(materials_list_upd))

        abstract_materials_upd_3 = cleaning_names(abstract_materials_upd_2)
        targets_upd_3 = cleaning_names(targets_upd_2)
        precursors_upd_3 = cleaning_names(precursors)
        others_upd_3 = cleaning_names(others_upd_2)

        if self.__verbose:
            print("After cleaning up names:")
            print ('\tabstract:', abstract_materials_upd_3)
            print ('\ttargets:', targets_upd_3)
            print ('\tprecursors:', precursors_upd_3)

        # Parsing chemical formulas of materials
        if self.__verbose:
            print('Extracting chemical composition:')

        def chemical_structure(materials_list = []):
            materials_structures = {}
            fails = []
            for material in materials_list:
                t_struct = {}
                try:
                    t_struct = self.__mp.get_chemical_structure(material)
                except:
                    t_struct['composition'] = {}
                    # print ('Failed: '+material)
                    fails.append(material)
                if len(t_struct['composition']) > 1:
                    materials_structures[material] = t_struct
            return materials_structures, fails

        abstract_materials_struct, fails['abstracts'] = chemical_structure(abstract_materials_upd_3)
        targets_struct, fails['targets'] = chemical_structure(targets_upd_3)
        precursors_struct, fails['precursors'] = chemical_structure(precursors_upd_3)
        others_struct, fails['others'] = chemical_structure(others_upd_3)

        # Resolving variables
        def resolve_valiables(materials_structures = {}):

            for material, struct in materials_structures.items():
                for var in struct['fraction_vars']:
                    values, mode = self.get_values(var, syn_paragraph)
                    if len(values) == 0:
                        values, mode = self.get_values(var, abstract)
                        if values == []:
                            values = [0.0]
                    struct['fraction_vars'][var] = values

                for var in struct['elements_vars']:
                    values, mode = self.get_values(var, syn_paragraph, elements=True)
                    if len(values) == 0:
                        values, mode = self.get_values(var, abstract, elements=True)
                    struct['elements_vars'][var] = values

            return materials_structures

        abstract_materials_struct = resolve_valiables(abstract_materials_struct)
        targets_struct = resolve_valiables(targets_struct)

        for material, struct in precursors_struct.items():
            for el, val in struct['elements_vars'].items():
                for t_struct in targets_struct.values():
                    if el in t_struct['elements_vars']:
                        struct['elements_vars'][el] = t_struct['elements_vars'][el]

        if self.__verbose:
            print('Materials structures from abstract:')
            pprint(abstract_materials_struct)
            print('Materials structures from targets:')
            pprint(targets_struct)
            print('Materials structures from precursors:')
            pprint(precursors_struct)

        #assigning possible abbreviations:
        for name, struct in abstract_materials_struct.items():
            struct['is_abbreviation_like'] = self.is_abbreviation_like(struct)

        for name, struct in targets_struct.items():
            struct['is_abbreviation_like'] = self.is_abbreviation_like(struct)

        if targets_struct == {}:
            targets_struct = abstract_materials_struct
        final_targets = {name: struct for name, struct in targets_struct.items() if struct['composition'] != {} and not struct['is_abbreviation_like']}
        # for name, struct in abstract_materials_struct.items():
        #     if not name in final_targets and struct['composition'] != {} and not struct['is_abbreviation_like']: #compare with precursors as well
        #         final_targets[name] = struct

        mer_materials = dict(
            abstract=abstract_materials,
            targets=targets,
            precursors=precursors,
            others = others
        )

        data_structure['targets'] = final_targets
        data_structure['precursors'] = precursors_struct
        data_structure['abstract'] = abstract_materials_struct
        data_structure['others'] = others_struct

        return data_structure, mer_materials, fails


    ###############################################################################################################

    def get_reactions(self, targets_list, precursors_list, split_mixture=True):

        all_targets = targets_list.copy()
        all_precursors = precursors_list.copy()
        reactions_list = []

        # Splitting mixtures if required
        if split_mixture:
            mixtures = [material for material, struct in all_targets.items() if struct['mixture'] != {}]
            for material in mixtures:
                struct = all_targets[material]
                for compound, compos in struct['mixture'].items():
                    if compound not in all_targets:
                        all_targets[compound] = {}
                        all_targets[compound]['chemical_name'] = ''
                        all_targets[compound]['composition'] = compos['composition']
                        all_targets[compound]['elements_vars'] = struct['elements_vars']
                        if any(not v.replace('.', '').replace('/','').isdigit() for v in compos['composition'].values()):
                            all_targets[compound]['fraction_vars'] = struct['fraction_vars']
                        else:
                            all_targets[compound]['fraction_vars'] = {}
                        all_targets[compound]['formula'] = compound
                        all_targets[compound]['name'] = struct['name']
                        all_targets[compound]['phase'] = struct['phase']
                        all_targets[compound]['mixture'] = {}
                del all_targets[material]


        if self.__verbose:
            print('List of targets after splitting:')
            pprint(all_targets)

        # Substitute values in precursors first
        all_precursors_upd = {}
        for material, struct in all_precursors.items():
            if struct['elements_vars'] == {}:
                all_precursors_upd[material] = struct
            else:
                for el, values in struct['elements_vars'].items():
                    for v in values:
                        new_struct = {}
                        new_struct['composition'] = struct['composition'].copy()
                        new_struct['composition'][v] = struct['composition'][el]
                        del new_struct['composition'][el]
                        new_struct['chemical_name'] = ''
                        new_struct['elements_vars'] = collections.defaultdict(str)
                        new_struct['fraction_vars'] = collections.defaultdict(str)
                        new_struct['formula'] = ''.join([e + self.__cast_stoichiometry(v) for e,v in sorted(new_struct['composition'].items())])
                        new_struct['is_abbreviation_like'] = False
                        new_struct['mixture'] = {}
                        new_struct['name'] = struct['name']
                        new_struct['phase'] = ''

                        all_precursors_upd[new_struct['formula']] = new_struct

        #if all_precursors_upd != {}:
        all_precursors = all_precursors_upd
        #     print('Substitution in precursors:')
        #     pprint(all_precursors_upd)

        if self.__verbose:
            print('List of list of precursors after substitution:')
            pprint(all_precursors)


        # Obtaining values to substitute
        for material, struct in all_targets.items():
            elements_array = self.get_substitutions_array(struct['elements_vars'])

            new_materials_array = []
            for subs in elements_array:
                composition = struct['composition'].copy()
                for var, val in subs.items():
                    composition[val] = composition[var]
                    del composition[var]
                new_materials_array.append(dict(
                    el_subst=subs,
                    composition=composition,
                    fraction_vars=struct['fraction_vars'].copy()
                ))

            if len(new_materials_array) == 0:
                new_materials_array.append(dict(
                    el_subst = {},
                    composition = struct['composition'].copy(),
                    fraction_vars = struct['fraction_vars'].copy()
                ))

            fractions_array = self.get_substitutions_array(struct['fraction_vars'])
            new_compositions = []
            for item in new_materials_array:
                if len(fractions_array) > 0:
                    for subs in fractions_array:
                        composition = item['composition'].copy()
                        obtained = True
                        for el, stoich in composition.items():
                            for var, val in subs.items():
                                stoich = stoich.replace(var, str(val))
                            try:
                                stoich = round(float(eval(stoich)), 3)
                                if stoich < 0:
                                    obtained = False
                            except:
                                obtained = False

                            composition[el] = str(stoich)

                        if obtained:
                            new_compositions.append(dict(
                                compos=composition,
                                subs=item['el_subst'],
                            ))

                else:
                    composition = item['composition'].copy()
                    obtained = True
                    for el, stoich in composition.items():
                        try:
                            stoich = round(float(eval(stoich)), 3)
                            if stoich < 0:
                                obtained = False
                        except:
                            obtained = False

                        composition[el] = str(stoich)

                    if obtained and all(composition != c['compos'] for c in new_compositions):
                        new_compositions.append(dict(
                            compos=composition,
                            subs=item['el_subst']
                        ))

            for composition in new_compositions:
                try:
                    correct_formula = self.reconstruct_formula(material, composition)
                except:
                    correct_formula = ''

                formula = ''
                zero_vals = []
                for el, val in composition['compos'].items():
                    if float(val) != 0.0:
                        formula = formula + el + self.__cast_stoichiometry(val)
                    else:
                        zero_vals.append(el)
                for el in zero_vals:
                    del composition['compos'][el]

                precursors = []
                for prec, p_struct in all_precursors.items():
                    if self.__is_precursor(p_struct['composition'], composition['compos']) and prec not in all_targets:
                        precursors.append(prec)

                if len(precursors) > 1:
                    reactions_list.append(dict(
                        formula = formula,
                        correct_formula = correct_formula,
                        #composition = composition['compos'],
                        #substitutions = composition['subs'],
                        precursors = precursors,
                        #precursors_compositions = {prec: precursors_struct[prec]['composition'] for prec in precursors},
                        #all_precursors = precursors_struct,
                        #doi = doi,
                        #syn_paragraph = syn_paragraph,
                        #abstract = abstract
                    ))


        return reactions_list


    def get_values(self,var, text, elements=False):

        values = []
        mode = ''
        sents = Paragraph(text).sentences
        i = 0
        try:
            while len(values) == 0 and i < len(sents):
                if elements:
                    values = self.__mp.get_elements_values(var, sents[i].text.strip('., '))
                else:
                    values, mode = self.__mp.get_stoichiometric_values(var, sents[i].text.strip('.'))
                i = i + 1
        except:
            values = []
            mode = ''
            # fails_var.append(data)

        return values, mode

    def get_substitutions_array(self, subs_dict):

        """
        Generate combinations of different variables values
        I.e. if 'x' = [0.1, 0.2] and 'y' = [0.5, 0.6], then outputs: [
        {'x': 0.1, 'y': 0.5}, {'x': 0.1, 'y': 0.6}, {'x': 0.2, 'y': 0.5},  {'x': 0.2, 'y': 0.6}]
        :return:
        """

        subs_array = []

        l_dict = len(subs_dict)
        t_array = [dict(var=k, val=v) for k, vs in subs_dict.items() for v in vs]

        for comb in itertools.combinations(range(0, len(t_array)), l_dict):
            s = ''.join([t_array[i]['var'] for i in comb])
            if len(s) == len(set(s)):
                t_dict = {}
                for i in comb:
                    t_dict[t_array[i]['var']] = t_array[i]['val']
                subs_array.append(t_dict)

        return subs_array

    def is_abbreviation_like(self, structure):
        if len(structure['elements_vars']) > 1 and \
                all(len(values) == 0 for values in structure['elements_vars'].values()):
            return True

        if all(el[0].isupper() and len(el) == 1 and value in ['1', '1.0'] for el, value in structure['composition'].items()) \
                and structure['composition'] != {}:
            return True

        if any(all(el[0].isupper() and len(el) == 1 and v in ['1', '1.0'] for el, v in compos['composition'].items()) for compos in structure['mixture'].values()):
            return True

        return False

    def reconstruct_formula(self, init_formula, data):
        new_formula = ''

        r = '[A-Z]{1}[a-wyz]{0,1}'
        elements = re.findall(r, init_formula)
        if len(elements) == len(data['compos']):
            if all(el in data['compos'] for el in elements):
                new_formula = ''.join([el + self.__cast_stoichiometry(data['compos'][el]) for el in elements])
            else:
                for el in elements:
                    if el not in self.__list_of_elements_2 and len(el) == 2 and el not in data['subs']:
                        el = el[0]
                    if el in data['compos']:
                        new_formula = new_formula + el + self.__cast_stoichiometry(data['compos'][el])
                    elif el in data['subs']:
                        el_ = data['subs'][el]
                        new_formula = new_formula + el_ + self.__cast_stoichiometry(data['compos'][el_])
                    else:
                        new_formula = ''

        new_formula = new_formula.replace('1.0', '')

        return new_formula

    def __is_precursor(self, p_composition, t_composition):

        for l in self.__greek_letters:
            _clash[l] = sympy.Symbol(l)

        if any( not sympy.sympify(v, _clash).is_Number for v in p_composition.values()):
            return False

        precursors__me = [p for p in p_composition.keys() if p not in ['0', 'H', 'N', 'C', 'P']]
        target__me = [p for p in t_composition.keys() if p not in ['0', 'H', 'N', 'C', 'P']]
        if len(precursors__me) > len(target__me):
            return False

        if any(el in p_composition for el in t_composition.keys() if el not in ['O', 'H', 'C']) \
                and t_composition.keys() != p_composition.keys():
            return True

        return False

    def __cast_stoichiometry(self, value):

        value = float(value)
        if value == 1.0:
            return ''
        if value * 1000 % 1000 == 0.0:
            return str(int(value))

        return str(value)


