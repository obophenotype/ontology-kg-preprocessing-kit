import os
import pandas as pd
from subprocess import check_call
import urllib.request
import yaml
import warnings
import re
import shutil

class okpk_config:
    def __init__(self, config_file):
        self.config = yaml.load(open(config_file, 'r'))

    def get_curie_map(self):
        return self.config.get("curie_map")
        
    def get_value_map(self,id,e0,e1,e2):
        map = dict()
        for t in self.config.get(e0):
            if t['id'] == id:   
                if e1 in t:
                    for r in t.get(e1):
                        if e2 in r:
                            map[r['id']] = r[e2]
        return map
    
    def get_biolink_relation_map(self,id):
        relations = dict()
        for t in self.config.get("global").get("relations"):
            if "biolink" in t:
                relations[t['id']] = r["biolink"]
        relations.update(self.get_value_map(id,"ontologies","relations","biolink"))
        return relations

    def get_biolink_category_map(self,id):
        return self.get_value_map(id,"ontologies","roots","biolink")
        
    def get_role_chains(self, id):
        return self.get_value_map(id,"ontologies","relations","chains")

    def get_ontologies(self):
        return [t['id'] for t in self.config.get("ontologies")]
        
    def get_remove_disjoints(self):
        return self.config.get("remove_disjoints")

    def get_remove_blacklist(self):
        return self.config.get("remove_blacklist")
        
    def get_dependencies(self, id):
        dependencies = []
        dependencies.extend(self.config.get("common_dependencies"))
        try:
            odeps = [t['dependencies'] for t in self.config.get("sources") if t['id'] == id][0]
            dependencies.extend(odeps)
        except:
            print("No dependencies for "+id)

        return dependencies

    def get_taxon_label(self, id):
        return [t['taxon_label'] for t in self.config.get("sources") if t['id'] == id][0]

    def get_taxon(self, id):
        return [t['taxon'] for t in self.config.get("sources") if t['id'] == id][0]

    def get_prefix_iri(self, id):
        return [t['prefix_iri'] for t in self.config.get("sources") if t['id'] == id][0]

    def get_roots(self, id):
        roots = []
        for t in self.config.get("ontologies"):
            if (t['id'] == id) & ("roots" in t):
                for root in t['roots']:
                    roots.append(root['id'])
        if roots:
            return roots     
        else:   
            return ['owl:Thing']

    def is_clean_dir(self):
        return self.config.get("clean")

    def is_overwrite_matches(self):
        return self.config.get("overwrite_matches")

    def is_overwrite_ontologies(self):
        return self.config.get("overwrite_ontologies")

    def get_ontology_properties(self, id, materialize_only=False):
        props = []
        for t in self.config.get("ontologies"):
            if t['id'] == id:
                if "relations" in t:
                    for r in t.get("relations"):
                        if materialize_only:
                            if r['materialize'] == True:
                                props.append(r['id'])
                        else:
                            props.append(r['id'])
        return props
        
    def get_ontology_annotation_properties(self, id):
        relations = []
        for t in self.config.get("global").get("annotations"):
            relations.append(t['id'])
        return relations

    def get_external_timeout(self):
        return str(self.config.get("timeout_external_processes"))

    def get_global_properties(self):
        return self.config.get("global").get("relations")

    def get_working_directory(self):
        return self.config.get("working_directory")

    def get_robot_opts(self):
        return self.config.get("robot_opts")

    def get_sources(self,id):
        return [t['sources'] for t in self.config.get("ontologies") if t['id'] == id][0]

    def get_instantiate_superclasses_pattern_vars(self):
        return self.config.get("instantiate_superclasses_pattern_vars")

    def get_robot_java_args(self):
        return self.config.get("robot_java_args")


def cdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def robot_extract_seed(ontology_path,seedfile,sparql_terms, TIMEOUT="60m", robot_opts="-v"):
    print("Extracting seed of "+ontology_path+" with "+sparql_terms)
    robot_query(ontology_path,seedfile,sparql_terms, TIMEOUT, robot_opts)

def robot_query(ontology_path,query_result,sparql_query, TIMEOUT="60m", robot_opts="-v",format='csv'):
    print("Querying "+ontology_path+" with "+sparql_query)
    try:
        check_call(['timeout',TIMEOUT,'robot', 'query',robot_opts,'--use-graphs','true','-f',format,'-i', ontology_path,'--query', sparql_query, query_result])
    except Exception as e:
        print(e.output)
        raise Exception("Querying {} with {} failed".format(ontology_path,sparql_query))

def robot_update(ontology_path,sparql_queries,ontology_out_path, TIMEOUT="60m", robot_opts="-v"):
    print("Querying "+ontology_path+" with "+str(sparql_queries))
    try:
        robot = ['timeout',TIMEOUT,'robot', 'query',robot_opts,'-i', ontology_path]
        for ru in sparql_queries:
            robot.extend(['--update', ru])
        robot.extend(['--output', ontology_out_path])
        check_call(robot)
    except Exception as e:
        print(e.output)
        raise Exception("Querying {} with {} failed".format(ontology_path,sparql_queries))

def robot_extract_module(ontology_path,seedfile, ontology_merged_path, TIMEOUT="60m", robot_opts="-v"):
    print("Extracting module of "+ontology_path+" to "+ontology_merged_path)
    try:
        check_call(['timeout',TIMEOUT,'robot', 'extract',robot_opts,'-i', ontology_path,'-T', seedfile,'--method','BOT', '--output', ontology_merged_path])
    except Exception as e:
        print(e.output)
        raise Exception("Module extraction of " + ontology_path + " failed")

def robot_dump_disjoints(ontology_path,term_file, ontology_removed_path, TIMEOUT="60m", robot_opts="-v"):
    print("Removing disjoint class axioms from "+ontology_path+" and saving to "+ontology_removed_path)
    try:
        cmd = ['timeout',TIMEOUT,'robot', 'remove',robot_opts,'-i', ontology_path]
        if term_file:
            cmd.extend(['--term-file',term_file])
        cmd.extend(['--axioms','disjoint', '--output', ontology_removed_path])
        check_call(cmd)
    except Exception as e:
        print(e.output)
        raise Exception("Removing disjoint class axioms from " + ontology_path + " failed")

def robot_remove_terms(ontology_path,remove_list, ontology_removed_path, TIMEOUT="60m", robot_opts="-v"):
    print("Removing terms from "+ontology_path+" and saving to "+ontology_removed_path)
    try:
        cmd = ['timeout',TIMEOUT,'robot', 'remove',robot_opts,'-i', ontology_path]
        terms = []
        patterns = []
        for t in remove_list:
            if t.startswith("<"):
                patterns.append(t)
            elif t.startswith("http"):
                terms.append(t)
        for term in terms:
            cmd.extend(['--term', term])
        for pattern in patterns:
            cmd.extend(['remove','--select', pattern])
        cmd.extend(['--output', ontology_removed_path])
        print(str(cmd))
        check_call(cmd)
    except Exception as e:
        print(e.output)
        raise Exception("Removing disjoint class axioms from " + ontology_path + " failed")

def robot_remove_mentions_of_nothing(ontology_path, ontology_removed_path, TIMEOUT="60m", robot_opts="-v"):
    print("Removing mentions of nothing from "+ontology_path+" and saving to "+ontology_removed_path)
    try:
        check_call(['timeout',TIMEOUT,'robot', 'remove',robot_opts,'-i', ontology_path,'--term','http://www.w3.org/2002/07/owl#Nothing', '--axioms','logical','--preserve-structure', 'false', '--output', ontology_removed_path])
    except Exception as e:
        print(e.output)
        raise Exception("Removing mentions of nothing from " + ontology_path + " failed")

def remove_all_sources_of_unsatisfiability(o, blacklist_ontology, TIMEOUT, robot_opts):
    robot_dump_disjoints(o, None, o, TIMEOUT, robot_opts)
    robot_remove_mentions_of_nothing(o, o, TIMEOUT, robot_opts)
    robot_remove_axioms_that_could_cause_unsat(o, o, TIMEOUT, robot_opts)
    if os.path.exists(blacklist_ontology):
        robot_remove_upheno_blacklist_and_classify(o, o, blacklist_ontology, TIMEOUT, robot_opts)

def robot_remove_axioms_that_could_cause_unsat(ontology_path, ontology_removed_path, TIMEOUT="60m", robot_opts="-v"):
    print("Removing axioms that could cause unsat from "+ontology_path+" and saving to "+ontology_removed_path)
    try:
        check_call(['timeout',TIMEOUT,'robot', 'remove',robot_opts,'-i', ontology_path, '--axioms','"DisjointClasses DisjointUnion DifferentIndividuals NegativeObjectPropertyAssertion NegativeDataPropertyAssertion FunctionalObjectProperty InverseFunctionalObjectProperty ReflexiveObjectProperty IrrefexiveObjectProperty ObjectPropertyDomain ObjectPropertyRange DisjointObjectProperties FunctionalDataProperty DataPropertyDomain DataPropertyRange DisjointDataProperties"','--preserve-structure', 'false', '--output', ontology_removed_path])
    except Exception as e:
        print(e.output)
        raise Exception("Removing mentions of nothing from " + ontology_path + " failed")

def robot_remove_upheno_blacklist_and_classify(ontology_path, ontology_removed_path, blacklist_ontology, TIMEOUT="3600", robot_opts="-v"):
    print("Removing upheno blacklist axioms from "+ontology_path+" and saving to "+ontology_removed_path)
    try:
        check_call(['timeout',TIMEOUT,'robot', 'merge',robot_opts,'-i', ontology_path,'unmerge', '-i', blacklist_ontology,'reason', '--reasoner','ELK', '--output', ontology_removed_path])
    except Exception as e:
        print(e.output)
        raise Exception("Removing mentions of nothing from " + ontology_path + " failed")

def robot_merge(ontology_list, ontology_merged_path, TIMEOUT="3600", robot_opts="-v", ONTOLOGYIRI="http://ontology.com/someuri.owl"):
    print("Merging " + str(ontology_list) + " to " + ontology_merged_path)
    try:
        callstring = ['timeout', TIMEOUT, 'robot', 'merge', robot_opts]
        merge = " ".join(["--input " + s for s in ontology_list]).split(" ")
        callstring.extend(merge)
        callstring.extend(["annotate", "--ontology-iri",ONTOLOGYIRI])
        callstring.extend(['--output', ontology_merged_path])
        check_call(callstring)
    except Exception as e:
        print(e)
        raise Exception("Merging of" + str(ontology_list) + " failed")

def list_files(directory, extension):
    return (f for f in os.listdir(directory) if f.endswith('.' + extension))

def dosdp_pattern_match(ontology_path, pattern_path, out_tsv, TIMEOUT="3600"):
    print("Matching " + ontology_path + " with " + pattern_path+" to "+out_tsv)
    try:
        check_call(['timeout', TIMEOUT, 'dosdp-tools', 'query', '--ontology='+ontology_path, '--reasoner=elk', '--obo-prefixes=true', '--template='+pattern_path,'--outfile='+out_tsv])
    except Exception as e:
        print(e)
        raise Exception("Matching " + str(ontology_path) + " for DOSDP: " + pattern_path + " failed")

def robot_prepare_ontology_for_dosdp(o, ontology_merged_path,sparql_terms_class_hierarchy, TIMEOUT="3600", robot_opts="-v"):
    """
    :param o: Input ontology
    :param ontology_merged_path: Output Ontology
    :param sparql_terms_class_hierarchy: SPARQL query that extracts seed
    :param TIMEOUT: Java timeout parameter. String. Using timeout command line program.
    :param robot_opts: Additional ROBOT options
    :return: Take o, extracts a seed using sparql_terms_class_hierarchy, extracts class hierarchy, merges both to ontology_merged_path.
    """
    print("Preparing " + str(o) + " for DOSDP: " + ontology_merged_path)
    subclass_hierarchy = os.path.join(os.path.dirname(ontology_merged_path),"class_hierarchy_"+os.path.basename(ontology_merged_path))
    subclass_hierarchy_seed = os.path.join(os.path.dirname(ontology_merged_path),
                                      "class_hierarchy_seed_" + os.path.basename(ontology_merged_path))
    robot_extract_seed(o, subclass_hierarchy_seed, sparql_terms_class_hierarchy, TIMEOUT, robot_opts)
    robot_class_hierarchy(o, subclass_hierarchy_seed,subclass_hierarchy,REASON=True,REMOVEDISJOINT=False,TIMEOUT=TIMEOUT,robot_opts=robot_opts)
    try:
        callstring = ['timeout', TIMEOUT, 'robot', 'merge', robot_opts,"-i",o,"-i",subclass_hierarchy]
        callstring.extend(['remove','--term', 'rdfs:label', '--select', 'complement', '--select', 'annotation-properties', '--preserve-structure', 'false'])
        callstring.extend(['--output', ontology_merged_path])
        check_call(callstring)
    except Exception as e:
        print(e)
        raise Exception("Preparing " + str(o) + " for DOSDP: " + ontology_merged_path + " failed")

def robot_upheno_release(ontology_list, ontology_merged_path, name, TIMEOUT="3600", robot_opts="-v",remove_terms=None):
    print("Finalising  " + str(ontology_list) + " to " + ontology_merged_path+", "+name)
    try:
        callstring = ['timeout', TIMEOUT, 'robot', 'merge', robot_opts]
        merge = " ".join(["--input " + s for s in ontology_list]).split(" ")
        callstring.extend(merge)
        callstring.extend(['remove', '--axioms', 'disjoint', '--preserve-structure', 'false'])
        callstring.extend(['remove', '--term','http://www.w3.org/2002/07/owl#Nothing', '--axioms','logical','--preserve-structure', 'false'])
        if remove_terms:
            callstring.extend(['remove', '-T', remove_terms, '--preserve-structure', 'false'])
        callstring.extend(['reason','--reasoner','ELK','reduce','--reasoner','ELK'])
        callstring.extend(['--output', ontology_merged_path])
        check_call(callstring)
    except Exception as e:
        print(e)
        raise Exception("Finalising " + str(ontology_list) + " failed...")

def robot_upheno_component(component_file,remove_eqs, TIMEOUT="3600", robot_opts="-v"):
    #robot remove --axioms "disjoint" --preserve-structure false reason --reasoner ELK -o /data/upheno_pre-fixed_mp-hp.owl
    print("Preparing uPheno component  " + str(component_file))
    try:
        callstring = ['timeout', TIMEOUT, 'robot', 'merge','-i',component_file]
        callstring.extend(['remove','-T',remove_eqs,'--axioms','equivalent','--preserve-structure','false'])
        callstring.extend(['--output', component_file])
        check_call(callstring)
    except Exception as e:
        print(e)
        raise Exception("Preparing uPheno component " + str(component_file) + " failed...")

def robot_children_list(o,query,outfile,TIMEOUT="3600",robot_opts="-v"):
    print("Extracting children from  " + str(o) +" using "+str(query))
    try:
        check_call(['timeout',TIMEOUT,'robot', 'query',robot_opts,'--use-graphs','true','-f','csv','-i', o,'--query', query, outfile])

    except Exception as e:
        print(e)
        raise Exception("Preparing uPheno component " + str(o) + " failed...")


def get_defined_phenotypes(upheno_config,pattern_dir,matches_dir):
    defined = []
    for pattern in os.listdir(pattern_dir):
        if pattern.endswith(".yaml"):
            tsv_file_name = pattern.replace(".yaml",".tsv")
            for oid in upheno_config.get_phenotype_ontologies():
                tsv = os.path.join(matches_dir,oid,tsv_file_name)
                if os.path.exists(tsv):
                    df = pd.read_csv(tsv, sep='\t')
                    defined.extend(df['defined_class'].tolist())
    return list(set(defined))


def robot_class_hierarchy(ontology_in_path, class_hierarchy_seed, ontology_out_path, REASON = True , TIMEOUT="3600", robot_opts="-v", REMOVEDISJOINT=False):
    print("Extracting class hierarchy from " + str(ontology_in_path) + " to " + ontology_out_path + "(Reason: "+str(REASON)+")")
    try:
        callstring = ['timeout', TIMEOUT, 'robot', 'merge', robot_opts,"--input",ontology_in_path]
        if REMOVEDISJOINT:
            callstring.extend(['remove','--axioms','disjoint','--preserve-structure', 'false'])
            callstring.extend(['remove','--term','http://www.w3.org/2002/07/owl#Nothing', '--axioms','logical','--preserve-structure', 'false'])

        if REASON:
            callstring.extend(['reason','--reasoner','ELK'])

        callstring.extend(['filter','-T',class_hierarchy_seed,'--axioms','subclass','--preserve-structure','false','--trim','false','--output', ontology_out_path])
        check_call(callstring)
    except Exception as e:
        print(e)
        raise Exception("Extracting class hierarchy from " + str(ontology_in_path) + " to " + ontology_out_path + " failed")


def dosdp_generate(pattern,tsv,outfile, RESTRICT_LOGICAL=False,TIMEOUT="3600",ONTOLOGY=None):
    try:
        callstring = ['timeout', TIMEOUT, 'dosdp-tools', 'generate', '--infile=' + tsv, '--template=' + pattern,
             '--obo-prefixes=true']
        if RESTRICT_LOGICAL:
            callstring.extend(['--restrict-axioms-to=logical'])
        if ONTOLOGY is not None:
            callstring.extend(['--ontology='+ONTOLOGY])
        callstring.extend(['--outfile=' + outfile])
        check_call(callstring)
    except:
        raise Exception("Pattern generation failed: "+pattern+", "+tsv+", "+outfile+".")


def dosdp_extract_pattern_seed(tsv_files,seedfile):
    classes = []
    try:
        for tsv in tsv_files:
            print("TSV:" +tsv)
            df = pd.read_csv(tsv, sep='\t')
            print(tsv+" done")
            classes.extend(df['defined_class'])
        with open(seedfile, 'w') as f:
            for item in list(set(classes)):
                f.write("%s\n" % item)
    except Exception as e:
        print(e)
        raise Exception("Extracting seed from all TSV files failed..")

def write_list_to_file(file_path,list):
    with open(file_path, 'w') as f:
        for item in list:
            f.write("%s\n" % item)

def touch(path):
    with open(path, 'a'):
        os.utime(path, None)

def rm(path):
    if os.path.isfile(path):
        os.remove(path)
    else:  ## Show an error ##
        print("Error: %s file not found" % path)
    
def robot_okpk_enrich(ontologies,materialize_props,ontology_path, TIMEOUT="60m", robot_opts="-v"):
    try:
        cmd = ['timeout',TIMEOUT]
        cmd.extend(['robot',robot_opts, 'merge'])
        for o in ontologies:
            cmd.extend(['-i', o])
        cmd.extend(['reason', '--reasoner', 'ELK'])
        if materialize_props:
            cmd.extend(['materialize', '--reasoner', 'ELK'])
            for p in materialize_props:
                cmd.extend(['--term', p])
        cmd.extend(['relax'])
        cmd.extend(['-o',ontology_path])
        check_call(cmd)
    except Exception as e:
        print(e.output)
        raise Exception("Running ROBOT Pipeline towards {} failed".format(ontology_path))
        
def robot_okpk_reduce(o,properties,ontology_path, TIMEOUT="60m", robot_opts="-v"):
    try:
        if properties:
            cmd = ['timeout',TIMEOUT]
            cmd.extend(['robot',robot_opts])
            
            cmd.extend(['remove', '-i',o])
            for p in properties:
                cmd.extend(['--term', p])
            cmd.extend(['--select','complement','--select', 'object-properties'])
            cmd.extend(['-o',ontology_path])
            check_call(cmd)
        else:
            shutil.copyfile(o, ontology_path)
    except Exception as e:
        print(e.output)
        raise Exception("Running ROBOT Pipeline towards {} failed".format(ontology_path))

def robot_okpk_finish(o,seed_file,ontology_path, TIMEOUT="60m", robot_opts="-v"):
    try:
        cmd = ['timeout',TIMEOUT]
        cmd.extend(['robot',robot_opts])
        cmd.extend(['filter', '-i',o])
        cmd.extend(['-T',seed_file])
        cmd.extend(['--signature','true'])
        cmd.extend(['-o',ontology_path])
        check_call(cmd)
    except Exception as e:
        print(e.output)
        raise Exception("Running ROBOT Pipeline towards {} failed".format(ontology_path))
        
def robot_convert(o,format,ontology_path, TIMEOUT="60m", robot_opts="-v"):
    try:
        cmd = ['timeout',TIMEOUT]
        cmd.extend(['robot',robot_opts])
        cmd.extend(['convert', '-i',o,'--format', format])
        cmd.extend(['-o',ontology_path])
        check_call(cmd)
    except Exception as e:
        print(e.output)
        raise Exception("Converting {} to {} failed".format(ontology_path,format))

def prepare_role_chains(o,role_chains,curie_map,role_chains_out_file):
    ontology = ['Prefix(:=<http://ontology-kg-preprocessing-kit.org/inject/{}_chains.owl#>)'.format(o)]
    ontology.append('Prefix(owl:=<http://www.w3.org/2002/07/owl#>)')
    ontology.append('Prefix(rdf:=<http://www.w3.org/1999/02/22-rdf-syntax-ns#>)')
    ontology.append('Prefix(xml:=<http://www.w3.org/XML/1998/namespace>)')
    ontology.append('Prefix(xsd:=<http://www.w3.org/2001/XMLSchema#>)')
    ontology.append('Prefix(rdfs:=<http://www.w3.org/2000/01/rdf-schema#>)')
    
    for curie in curie_map:
        ontology.append('Prefix({}:=<{}>)'.format(curie,curie_map.get(curie)))
    
    ontology.append('Ontology(<http://ontology-kg-preprocessing-kit.org/inject/{}_chains.owl>'.format(o))
    
    for rel in role_chains:
        for chain in role_chains.get(rel):
            chain_items = chain.split("|")
            chain_exp = "SubObjectPropertyOf(ObjectPropertyChain("
            for item in chain_items:
                chain_exp+=item+" "
            chain_exp+=") {})".format(rel)
            ontology.append(chain_exp)
        
    ontology.append(')')
    write_list_to_file(role_chains_out_file,ontology)

def download_from_urls(o,sources,o_build_dir,skip=False):
    i = 1
    downloads = []
    for s in sources:
        source_file = os.path.join(o_build_dir,'{}_source_{}.owl'.format(o,i))
        if not skip or not os.path.exists(source_file):
            urllib.request.urlretrieve(s,source_file)
        i += 1
        downloads.append(source_file)
    return downloads

def prepare_entities_of_interest(o,roots,properties,curie_map,query_file):
    sparql = get_default_sparql_header(curie_map)
    sparql.append('SELECT ?s ?p ?y WHERE ')
    sparql.append('{')
    sparql.append('?s rdfs:subClassOf* ?x . ')
    sparql.append('OPTIONAL { ?s rdfs:subClassOf [')
    sparql.append('a owl:Restriction ;')
    sparql.append('owl:onProperty ?p ;')
    sparql.append('owl:someValuesFrom ?y ] }')
    sparql.append('FILTER(isIRI(?s))')
    sparql.append('FILTER(!bound(?y) || isIRI(?y))')
    if roots:
        sparql.append(sparql_in_filter(roots,"x"))
    if properties:
        sparql.append(sparql_in_filter(properties,"p",True))
    sparql.append('}')
    write_list_to_file(query_file,sparql)


def prepare_ttl_biolink_relations(o,biolink_relations,curie_map,ttl_file):
    ttl = ['@prefix : <http://ontology-kg-preprocessing-kit.org/inject/{}_biolink_relations.owl> . '.format(o)]
    ttl.append('@prefix biolink: <https://w3id.org/biolink/vocab/> . ')
    ttl.append('@prefix owl: <http://www.w3.org/2002/07/owl#> . ')
    ttl.append('@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> . ')
    ttl.append('@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> . ')
    for curie in curie_map:
        ttl.append('@prefix {}: <{}> . '.format(curie,curie_map.get(curie)))
    ttl.append('@base <http://ontology-kg-preprocessing-kit.org/inject/{}_biolink_relations.owl> .'.format(o))
    ttl.append('<http://ontology-kg-preprocessing-kit.org/inject/{}_biolink_relations.owl> rdf:type owl:Ontology .'.format(o))
    ttl.append('biolink:relation rdf:type owl:AnnotationProperty .')
    for rel in biolink_relations:
        ttl.append("{} rdf:type owl:ObjectProperty .".format(rel))
        ttl.append("{} biolink:relation {} .".format(rel,biolink_relations.get(rel)))
    write_list_to_file(ttl_file,ttl)
        

def prepare_sparql_biolink_annotations(o,biolink_categories,curie_map,query_folder):
    biolink_annotation_files = []
    i = 0
    for cl in biolink_categories:
        query_file = os.path.join(query_folder,"{}_biolink_{}.sparql".format(o,i))
        sparql = get_default_sparql_header(curie_map)
        sparql.append('INSERT {'+' ?s biolink:category {} '.format(biolink_categories.get(cl))+". } WHERE ")
        sparql.append('{')
        sparql.append('?s rdfs:subClassOf* ?x . ')
        sparql.append('FILTER(isIRI(?s))')
        sparql.append(sparql_in_filter([cl],"x"))
        sparql.append('}')
        write_list_to_file(query_file,sparql)
        biolink_annotation_files.append(query_file)
        i += 1
    return biolink_annotation_files

def sparql_in_filter(l,variable,isBoundClause=False):
    boundclause=""
    if isBoundClause:
        boundclause="!bound(?{}) || ".format(variable)
    f1='FILTER({}?{} IN ('.format(boundclause,variable)
    for e in l:
        f1+=e+", "
    f1 = f1.strip()[:-1]
    f1+=')) '
    return f1

def get_default_sparql_header(curie_map):
    sparql = ['prefix owl: <http://www.w3.org/2002/07/owl#>']
    sparql.append('prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>')
    sparql.append('prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>')
    sparql.append('prefix skos: <http://www.w3.org/2004/02/skos/core#>')
    sparql.append('prefix biolink: <https://w3id.org/biolink/vocab/>')
    sparql.append('prefix dce: <http://purl.org/dc/elements/1.1/>')
    for curie in curie_map:
        sparql.append('prefix {}: <{}>'.format(curie,curie_map.get(curie)))
    return sparql

def prepare_sparql_count_object_properties(o,roots,curie_map,query_file):
    sparql = get_default_sparql_header(curie_map)
    sparql.append('SELECT ?p (COUNT(?p) as ?pCount) WHERE ')
    sparql.append('{')
    sparql.append('?s rdfs:subClassOf* ?x . ')
    sparql.append('?s rdfs:subClassOf [')
    sparql.append('a owl:Restriction ;')
    sparql.append('owl:onProperty ?p ;')
    sparql.append('owl:someValuesFrom ?y ]  .')
    sparql.append('FILTER(isIRI(?s))')
    sparql.append('FILTER(isIRI(?y))')
    if roots:
        sparql.append(sparql_in_filter(roots,"x"))
    sparql.append('}')
    sparql.append('GROUP BY ?p ')
    write_list_to_file(query_file,sparql)

def prepare_sparql_count_annotation_properties(o,roots,curie_map,query_file):
    sparql = get_default_sparql_header(curie_map)
    sparql.append('SELECT ?p (COUNT(?p) as ?pCount) WHERE ')
    sparql.append('{')
    sparql.append('?s rdfs:subClassOf* ?x . ')
    sparql.append('?s ?p ?y .') 
    sparql.append('?p a owl:AnnotationProperty  .')
    sparql.append('FILTER(isIRI(?s))')
    if roots:
        sparql.append(sparql_in_filter(roots,"x"))
    sparql.append('}')
    sparql.append('GROUP BY ?p ')
    write_list_to_file(query_file,sparql)

def prepare_seed_file(o_seed_table,annotation_properties,o_seed):
    seed_df = pd.read_csv(o_seed_table)
    seed_list = []
    seed_list.extend(seed_df['s'].to_list())
    seed_list.extend(seed_df['p'].to_list())
    seed_list.extend(seed_df['y'].to_list())
    seed_list = list(set(seed_list))
    for p in annotation_properties:
        seed_list.append(p)
    write_list_to_file(o_seed,seed_list)
