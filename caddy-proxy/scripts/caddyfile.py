template = {}

servers_old= {
    "test_server": {
        "listen": [""],
        "listener_wrappers": [{}],
        "read_timeout": 0,
        "read_header_timeout": 0,
        "write_timeout": 0,
        "idle_timeout": 0,
        "max_header_bytes": 0,
        "routes": [{
            "group": "",
            "match": [{}],
            "handle": [{
                "handler": "file_server",
                "root": "/var/www"
            }],
            "terminal": False
        }],
        "errors": {
            "routes": [{
                "group": "",
                "match": [{}],
                "handle": [{}],
                "terminal": False
            }]
        },
        "tls_connection_policies": [{
            "match": {},
            "certificate_selection": {
                "serial_number": [{
                }],
                "subject_organization": [""],
                "public_key_algorithm": 0,
                "any_tag": [""],
                "all_tags": [""]
            },
            "cipher_suites": [""],
            "curves": [""],
            "alpn": [""],
            "protocol_min": "",
            "protocol_max": "",
            "client_authentication": {
                "trusted_ca_certs": [""],
                "trusted_ca_certs_pem_files": [""],
                "trusted_leaf_certs": [""],
                "mode": ""
            },
            "default_sni": ""
        }],
        "automatic_https": {
            "disable": False,
            "disable_redirects": False,
            "skip": [""],
            "skip_certificates": [""],
            "ignore_loaded_certificates": False
        },
        "strict_sni_host": False,
        "logs": {
            "default_logger_name": "",
            "logger_names": {
                "": ""
            },
            "skip_hosts": [""],
            "skip_unmapped_hosts": False
        },
        "experimental_http3": False,
        "allow_h2c": False
    }
}