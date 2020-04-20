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
from lib import cdir, rm, touch, okpk_config, robot_query, write_list_to_file, robot_update, robot_merge

### Configuration
warnings.simplefilter('ignore', ruamel.yaml.error.UnsafeLoaderWarning)

config_file = sys.argv[1]
print(config_file)
config = okpk_config(config_file)

TIMEOUT=str(config.get_external_timeout())
ws = config.get_working_directory()
robot_opts=config.get_robot_opts()

ontology_dir = os.path.join("ontologies")
build_dir = os.path.join(os.environ['BUILDDIR'])
sparql_dir = os.path.join(os.environ['SPARQLDIR'])

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
        cmd.extend(['reason', '--reasoner', 'ELK', 'reduce','--reasoner', 'ELK'])
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
        cmd = ['timeout',TIMEOUT]
        cmd.extend(['robot',robot_opts])
        cmd.extend(['remove', '-i',o])
        for p in properties:
            cmd.extend(['--term', p])
        cmd.extend(['--select','complement','--select', 'object-properties'])
        cmd.extend(['-o',ontology_path])
        check_call(cmd)
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
    sparql.append('SELECT ?s ?p ?y ?ap WHERE ')
    sparql.append('{')
    sparql.append('?s rdfs:subClassOf* ?x . ')
    sparql.append('?s rdfs:subClassOf [')
    sparql.append('a owl:Restriction ;')
    sparql.append('owl:onProperty ?p ;')
    sparql.append('owl:someValuesFrom ?y ]  .')
    sparql.append('FILTER(isIRI(?s))')
    sparql.append('FILTER(isIRI(?y))')
    sparql.append(sparql_in_filter(roots,"x"))
    sparql.append(sparql_in_filter(properties,"p"))
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
        query_file = os.path.join(o_build_dir,"{}_biolink_{}.sparql".format(o,i))
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

def sparql_in_filter(l,variable):
    f1='FILTER(?{} IN ('.format(variable)
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


common_properties = config.get_global_properties()
kgx_nodes_sparql = os.path.join(sparql_dir,"kgx_nodes.sparql")
kgx_edges_sparql = os.path.join(sparql_dir,"kgx_edges.sparql")
kgx_annotations_sparql = os.path.join(sparql_dir,"kgx_annotations.sparql")
construct_kgx_types_sparql = os.path.join(sparql_dir,"construct_kgx_types.sparql")

skip = True

for o in config.get_ontologies():
    print("### Preparing {} ###".format(o))
    o_build_dir = os.path.join(build_dir,o)
    o_ontology_dir = os.path.join(ontology_dir,o)
    o_role_chains = os.path.join(o_build_dir,"role_chains_{}.owl".format(o))
    o_seed_table = os.path.join(o_build_dir,"seed_{}.csv".format(o))
    o_seed = os.path.join(o_build_dir,"seed_{}.txt".format(o))
    o_seed_sparql = os.path.join(o_build_dir,"seed_{}.sparql".format(o))
    o_biolink_sparql = os.path.join(o_build_dir,"biolink_{}.sparql".format(o))
    o_biolink_category_ttl  = os.path.join(o_build_dir,"biolink_categories_{}.ttl".format(o))
    o_biolink_relations_ttl  = os.path.join(o_build_dir,"biolink_relations_{}.ttl".format(o))
    o_biolink_update_sparql = os.path.join(o_build_dir,"biolink_update_{}.sparql".format(o))
    o_count_object_properties_sparql = os.path.join(o_build_dir,"count_object_properties_{}.sparql".format(o))
    o_count_annotation_properties_sparql = os.path.join(o_build_dir,"count_annotation_properties_{}.sparql".format(o))
    o_count_object_properties_csv = os.path.join(o_ontology_dir,"count_object_properties_{}.csv".format(o))
    o_count_annotation_properties_csv = os.path.join(o_ontology_dir,"count_annotation_properties_{}.csv".format(o))
    o_enriched = os.path.join(o_build_dir,"{}_enriched.owl".format(o))
    o_reduced = os.path.join(o_build_dir,"{}_reduced.owl".format(o))
    o_finished = os.path.join(o_ontology_dir,"{}_finished.owl".format(o))
    o_biolink = os.path.join(o_build_dir,"{}_biolink.owl".format(o))
    o_kg_json = os.path.join(o_ontology_dir,"{}_kg.json".format(o))
    o_kg_nodes_tsv = os.path.join(o_ontology_dir,"kgx_{}_nodes.csv".format(o))
    o_kg_edges_tsv = os.path.join(o_ontology_dir,"kgx_{}_edges.csv".format(o))
    o_kg_annotations_tsv = os.path.join(o_ontology_dir,"kgx_{}_annotations.csv".format(o))
    
    cdir(o_build_dir)
    cdir(o_ontology_dir)
    
    # Config
    o_roots = config.get_roots(o)
    o_properties = config.get_ontology_properties(o)
    o_annotation_properties = config.get_ontology_annotation_properties(o)
    o_materialise_properties = config.get_ontology_properties(o,True)
    
    # Prepare SPARQL queries and OWL injections
    prepare_role_chains(o,config.get_role_chains(o),config.get_curie_map(),o_role_chains)
    prepare_sparql_count_object_properties(o,o_roots,config.get_curie_map(),o_count_object_properties_sparql)
    prepare_sparql_count_annotation_properties(o,o_roots,config.get_curie_map(),o_count_annotation_properties_sparql)
    prepare_entities_of_interest(o,o_roots,o_properties,config.get_curie_map(),o_seed_sparql)
    prepare_ttl_biolink_relations(o,config.get_biolink_relation_map(o),config.get_curie_map(),o_biolink_relations_ttl)
    biolink_annotations_sparqls = prepare_sparql_biolink_annotations(o,config.get_biolink_category_map(o),config.get_curie_map(),o_biolink_update_sparql)
    
    print("### Downloading {} ###".format(o))
    o_merge_list = download_from_urls(o,config.get_sources(o),o_build_dir,skip)
    o_merge_list.append(o_role_chains)
    
    print("### Running ROBOT Enrich Pipeline {} ###".format(o))
    if not skip or not os.path.exists(o_enriched):
        robot_okpk_enrich(o_merge_list,o_materialise_properties,o_enriched)
    if not skip or not os.path.exists(o_count_annotation_properties_csv):
        robot_query(o_enriched,o_count_annotation_properties_csv,o_count_annotation_properties_sparql)
    if not skip or not os.path.exists(o_count_object_properties_csv):
        robot_query(o_enriched,o_count_object_properties_csv,o_count_object_properties_sparql)
    
    print("### Get all the classes that touch the classes of interest in {} ###".format(o))
    if not skip or not os.path.exists(o_reduced):
        robot_okpk_reduce(o_enriched,o_properties,o_reduced)
    if not skip or not os.path.exists(o_seed):
        robot_query(o_reduced,o_seed_table,o_seed_sparql)
        prepare_seed_file(o_seed_table,o_annotation_properties,o_seed)
    
    if not skip or not os.path.exists(o_finished): 
        robot_okpk_finish(o_reduced,o_seed,o_finished)
    
    print("### Export {} to obographs ###".format(o))
    if not skip or not os.path.exists(o_kg_json): 
        robot_convert(o_finished,"json",o_kg_json)

    print("### Export {} to tsv ###".format(o))
    if not skip or not os.path.exists(o_biolink):
        robot_update(o_enriched,biolink_annotations_sparqls,o_biolink)
        robot_query(o_biolink,o_biolink_category_ttl,construct_kgx_types_sparql,format='ttl')
        robot_merge([o_finished,o_biolink_category_ttl,o_biolink_relations_ttl],o_biolink)
    if not skip or not os.path.exists(o_kg_nodes_tsv):
        robot_query(o_biolink,o_kg_nodes_tsv,kgx_nodes_sparql)
    if not skip or not os.path.exists(o_kg_edges_tsv):
        robot_query(o_biolink,o_kg_edges_tsv,kgx_edges_sparql)
    if not skip or not os.path.exists(o_kg_annotations_tsv):
        robot_query(o_biolink,o_kg_annotations_tsv,kgx_annotations_sparql)



