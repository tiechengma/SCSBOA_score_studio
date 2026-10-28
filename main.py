import sys

if __name__=='__main__':
    if len(sys.argv)>2 and sys.argv[1]=='--verify-install':
        from scorestudio.diagnostics import verify
        raise SystemExit(verify(sys.argv[2],sys.argv[3] if len(sys.argv)>3 else None))
    from scorestudio.app import main
    raise SystemExit(main())
