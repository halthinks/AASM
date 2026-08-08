from aasm.cli import build_parser

def test_cli_exposes_durable_commands():
    parser=build_parser()
    for argv,command in [(["demo"],"demo"),(["runs","--db","x.db"],"runs"),(["replay","machine_x","--db","x.db"],"replay"),(["fork","machine_x","--db","x.db","--at","3"],"fork"),(["verify-machine","machine.json"],"verify-machine"),(["inspect","machine_x","--db","x.db"],"inspect"),(["plan","machine_x","--db","x.db"],"plan"),(["memory","machine_x","--db","x.db"],"memory"),(["evidence","machine_x","--db","x.db"],"evidence")]: assert parser.parse_args(argv).command==command

def test_cli_verify_machine_reports_valid(tmp_path,capsys):
    from aasm.cli import main
    import json,sys
    path=tmp_path/'machine.json'; path.write_text(json.dumps({'name':'ok','start_state':'A','terminal_states':['DONE'],'transitions':{'A':['DONE'],'DONE':[]}})); old=sys.argv
    try: sys.argv=['aasm','verify-machine',str(path)]; main()
    finally: sys.argv=old
    assert '"valid": true' in capsys.readouterr().out
