import csv

'''
Módulo para exportar los registros de flujo de fondos a CSV.
'''
def export_fund_flow_records_to_csv(records, filepath):
    with open(filepath, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'seed_case', 'path_id', 'hop', 'follow', 'input', 'output', 'wallet_explorer_id',
            'wallet_classification', 'wallet_label', 'txid', 'datetime_CET', 'mov_type', 'BTC',
            'classification', 'BTC_added_to_flow_from_others', 'BTC_not_followed', 'notes'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for record in sorted(records, key=lambda r: (r.path_id, r.hop)):
            # Los número decimales se formatean con 10 decimales
            writer.writerow({
                'seed_case': record.seed_case,
                'path_id': record.path_id,
                'hop': record.hop,
                'follow': record.follow,
                'input': record.input,
                'output': record.output,
                'wallet_explorer_id': record.wallet_explorer_id,
                'wallet_classification': record.wallet_classification,
                'wallet_label': record.wallet_label,
                'txid': record.txid,
                'datetime_CET':  record.datetime_CET.strftime('%Y-%m-%d %H:%M:%S') if record.datetime_CET else '',
                'mov_type': record.mov_type,
                'BTC': f"{record.BTC:.10f}",
                'classification': record.classification,
                'BTC_added_to_flow_from_others': f"{record.BTC_added_to_flow_from_others:.10f}",
                'BTC_not_followed': f"{record.BTC_not_followed:.10f}",
                'notes': record.notes
            })