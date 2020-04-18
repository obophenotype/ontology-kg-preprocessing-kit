#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 17 21:24:37 2020

@author: Nicolas Matentzoglu, EMBL-EBI
"""

import os, shutil, sys
import ruamel.yaml
import warnings
import urllib.request
import requests
import pandas as pd
import re
from subprocess import check_call,CalledProcessError
from lib import cdir, rm, touch, okpk_config, robot_query, write_list_to_file

### Configuration
warnings.simplefilter('ignore', ruamel.yaml.error.UnsafeLoaderWarning)

config_file = sys.argv[1]
print(config_file)
config = okpk_config(config_file)

TIMEOUT=str(config.get_external_timeout())
ws = config.get_working_directory()
robot_opts=config.get_robot_opts()

ontology_dir = os.path.join(ws,"ontologies")
build_dir = os.path.join(ws,"build")

cdir(ontology_dir)
cdir(build_dir)

if config.is_clean_dir():
    print("Cleanup..")
    shutil.rmtree(ontology_dir)
    os.makedirs(ontology_dir)
    shutil.rmtree(build_dir)
    os.makedirs(build_dir)


print("### Building Ontologies ###")

def robot_okpk_enrich(ontologies,materialize_props,ontology_path, TIMEOUT="60m", robot_opts="-v"):
    try:
        cmd = ['timeout',TIMEOUT]
        cmd.extend(['robot',robot_opts, 'merge'])
        for o in ontologies:
            cmd.extend(['-i', o])
        cmd.extend(['reason', '--reasoner', 'ELK'])
        cmd.extend(['materialize', '--reasoner', 'ELK'])
        for p in materialize_props:
            cmd.extend(['--term', p])
        cmd.extend(['-o',ontology_path])
        check_call(cmd)
    except Exception as e:
        print(e.output)
        raise Exception("Running ROBOT Pipeline towards {} failed".format(ontology_path))
        
def robot_okpk_reduce(o,properties,ontology_path, TIMEOUT="60m", robot_opts="-v"):
    try:
        cmd = ['timeout',TIMEOUT]
        cmd.extend(['robot',robot_opts, 'merge'])
        cmd.extend(['remove' '-i',o])
        for p in properties:
            cmd.extend(['--term', p])
        cmd.extend(['--select','complement','--select', 'object-properties'])
        cmd.extend(['-o',ontology_path])
        check_call(cmd)
    except Exception as e:
        print(e.output)
        raise Exception("Running ROBOT Pipeline towards {} failed".format(ontology_path))

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
        source_file = os.path.join(build_dir,'{}_source_{}.owl'.format(o,i))
        if not skip or not os.path.exists(source_file):
            urllib.request.urlretrieve(s,source_file)
        i += 1
        downloads.append(source_file)
    return downloads

def prepare_sparql_classes_of_interest(o,roots,properties,curie_map,query_file):
    sparql = get_default_sparql_header(curie_map)
    sparql.append('SELECT ?s ?p ?y WHERE ')
    sparql.append('{')
    sparql.append('?s rdfs:subClassOf* ?x . ')
    sparql.append('?s rdfs:subClassOf [')
    sparql.append('a owl:Restriction ;')
    sparql.append('owl:onProperty ?p ;')
    sparql.append('owl:someValuesFrom ?y ]  .')
    sparql.append('FILTER(isIRI(?s))')
    sparql.append('FILTER(isIRI(?y))')
    sparql.append(sparql_in_filter(roots))
    sparql.append(sparql_in_filter(properties))
    sparql.append('}')
    write_list_to_file(query_file,sparql)
    
def sparql_in_filter(l):
    f1='FILTER(?x IN ('
    for e in l:
        f1+=e+", "
    f1 = f1.strip()[:-1]
    f1+=')) '
    return f1

def get_default_sparql_header(curie_map):
    sparql = ['prefix owl: <http://www.w3.org/2002/07/owl#>']
    sparql.append('prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>')
    sparql.append('prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>')
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
    sparql.append(sparql_in_filter(roots))
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
    sparql.append(sparql_in_filter(roots))
    sparql.append('}')
    sparql.append('GROUP BY ?p ')
    write_list_to_file(query_file,sparql)

def prepare_seed_file(o_seed_table,o_seed):
    seed_df = pd.read_csv(o_seed_table)
    seed_list = []
    seed_list.extent(seed_df['x'].to_list())
    seed_list.extent(seed_df['p'].to_list())
    seed_list.extent(seed_df['y'].to_list())
    seed_list = list(set(seed_list))
    write_list_to_file(o_seed,seed_list)

common_properties = config.get_global_properties()
skip = True

for o in config.get_ontologies():
    print("### Preparing {} ###".format(o))
    o_build_dir = os.path.join(build_dir,o)
    o_role_chains = os.path.join(o_build_dir,"role_chains_{}.owl".format(o))
    o_seed_table = os.path.join(o_build_dir,"seed_{}.csv".format(o))
    o_seed = os.path.join(o_build_dir,"seed_{}.txt".format(o))
    o_seed_sparql = os.path.join(o_build_dir,"seed_{}.sparql".format(o))
    o_count_object_properties_sparql = os.path.join(o_build_dir,"count_object_properties_{}.sparql".format(o))
    o_count_annotation_properties_sparql = os.path.join(o_build_dir,"count_annotation_properties_{}.sparql".format(o))
    o_count_object_properties_csv = os.path.join(o_build_dir,"count_object_properties_{}.csv".format(o))
    o_count_annotation_properties_csv = os.path.join(o_build_dir,"count_annotation_properties_{}.csv".format(o))
    o_enriched = os.path.join(o_build_dir,"{}_enriched.owl".format(o))
    o_reduced = os.path.join(o_build_dir,"{}_reduced.owl".format(o))
    cdir(o_build_dir)
    
    # Config
    o_roots = config.get_roots(o)
    o_properties = config.get_ontology_properties(o)
    o_materialise_properties = config.get_ontology_properties(o,True)
    
    # Prepare SPARQL queries and OWL injections
    prepare_role_chains(o,config.get_role_chains(o),config.get_curie_map(),o_role_chains)
    prepare_sparql_count_object_properties(o,o_roots,config.get_curie_map(),o_count_object_properties_sparql)
    prepare_sparql_count_annotation_properties(o,o_roots,config.get_curie_map(),o_count_annotation_properties_sparql)
    prepare_sparql_classes_of_interest(o,o_roots,o_properties,config.get_curie_map(),o_seed_sparql)
    
    print("### Downloading {} ###".format(o))
    o_merge_list = download_from_urls(o,config.get_sources(o),o_build_dir,skip)
    o_merge_list.append(o_role_chains)
    
    print("### Running ROBOT Enrich Pipeline {} ###".format(o))
    robot_okpk_enrich(o_merge_list,o_materialise_properties,o_enriched)
    robot_query(o_enriched,o_count_annotation_properties_csv,o_count_annotation_properties_sparql)
    robot_query(o_enriched,o_count_object_properties_csv,o_count_object_properties_sparql)
    
    print("### Get all the classes that touch the classes of interest in {} ###".format(o))
    
    robot_okpk_reduce(o_enriched,o_properties,o_reduced)
    robot_query(o_reduced,o_seed_table,o_seed_sparql)
    prepare_seed_file(o_seed_table,o_seed)
    
    print("### ..pruning away all the rest ###".format(o))
    #robot_filter()
    
    print("### Export {} to obographs ###".format(o))
    print("### Export {} to tsv ###".format(o))


