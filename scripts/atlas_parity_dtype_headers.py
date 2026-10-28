"""Exact source-only wrapper schemas, independent of artifact checksums."""
from atlas_parity_schema import fields, need


def exact_fields(record, required, context):
    fields(record, required, context)
    need(set(record) == set(required), context + ': unexpected or missing fields')


def source_witness_header(document, citations):
    exact_fields(document, {'witnesses': dict, 'whole_api_or_runtime_credit': bool},
                 'dtype source witness credit header')
    need(document['whole_api_or_runtime_credit'] is False,
         'dtype source witness whole API/runtime credit forbidden')
    need(document['witnesses'].keys() == citations.keys(), 'dtype source witness identity set drift')
    for identity, witness in document['witnesses'].items():
        need(type(witness) is dict and set(witness) == set(citations[identity]) | {'text'},
             'dtype source witness contains unsupported metadata or credit claim')
