PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS stores (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    platform TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS operators (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    operator_id INTEGER NOT NULL REFERENCES operators(id)
);

CREATE TABLE IF NOT EXISTS products (
    store_id INTEGER NOT NULL REFERENCES stores(id),
    product_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    operator_id INTEGER NOT NULL REFERENCES operators(id),
    status TEXT NOT NULL DEFAULT 'active',
    PRIMARY KEY (store_id, product_id)
);

CREATE TABLE IF NOT EXISTS fact_store_daily (
    date TEXT NOT NULL,
    store_id INTEGER NOT NULL REFERENCES stores(id),
    pay_amount NUMERIC NOT NULL DEFAULT 0,
    refund_amount NUMERIC NOT NULL DEFAULT 0,
    ad_cost NUMERIC NOT NULL DEFAULT 0,
    visitors INTEGER NOT NULL DEFAULT 0,
    buyers INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (date, store_id)
);

CREATE TABLE IF NOT EXISTS fact_product_daily (
    date TEXT NOT NULL,
    store_id INTEGER NOT NULL REFERENCES stores(id),
    product_id TEXT NOT NULL,
    product_name TEXT,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    operator_id INTEGER NOT NULL REFERENCES operators(id),
    pay_amount NUMERIC NOT NULL DEFAULT 0,
    refund_amount NUMERIC NOT NULL DEFAULT 0,
    pay_qty INTEGER NOT NULL DEFAULT 0,
    visitors INTEGER NOT NULL DEFAULT 0,
    buyers INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (date, store_id, product_id),
    FOREIGN KEY (store_id, product_id) REFERENCES products(store_id, product_id)
);

CREATE TABLE IF NOT EXISTS fact_ad_daily (
    date TEXT NOT NULL,
    store_id INTEGER NOT NULL REFERENCES stores(id),
    product_id TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    operator_id INTEGER NOT NULL REFERENCES operators(id),
    cost NUMERIC NOT NULL DEFAULT 0,
    ad_gmv NUMERIC NOT NULL DEFAULT 0,
    PRIMARY KEY (date, store_id, product_id),
    FOREIGN KEY (store_id, product_id) REFERENCES products(store_id, product_id)
);

CREATE TABLE IF NOT EXISTS targets_store (
    month TEXT NOT NULL,
    store_id INTEGER NOT NULL REFERENCES stores(id),
    target_amount NUMERIC NOT NULL,
    PRIMARY KEY (month, store_id)
);

CREATE TABLE IF NOT EXISTS targets_category (
    month TEXT NOT NULL,
    store_id INTEGER NOT NULL REFERENCES stores(id),
    category_id INTEGER NOT NULL REFERENCES categories(id),
    target_amount NUMERIC NOT NULL,
    PRIMARY KEY (month, store_id, category_id)
);

CREATE TABLE IF NOT EXISTS targets_operator (
    month TEXT NOT NULL,
    operator_id INTEGER NOT NULL REFERENCES operators(id),
    target_amount NUMERIC NOT NULL,
    PRIMARY KEY (month, operator_id)
);

CREATE TABLE IF NOT EXISTS import_logs (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_sha256 TEXT NOT NULL,
    data_date TEXT NOT NULL,
    inserted_rows INTEGER NOT NULL DEFAULT 0,
    updated_rows INTEGER NOT NULL DEFAULT 0,
    skipped_rows INTEGER NOT NULL DEFAULT 0,
    unmatched_rows INTEGER NOT NULL DEFAULT 0,
    archive_path TEXT
);

CREATE TABLE IF NOT EXISTS column_map_profiles (
    id INTEGER PRIMARY KEY,
    store_id INTEGER NOT NULL REFERENCES stores(id),
    file_type TEXT NOT NULL,
    header_signature TEXT NOT NULL,
    sheet_name TEXT,
    header_row INTEGER NOT NULL,
    data_start_row INTEGER NOT NULL,
    row_filter TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (store_id, file_type, header_signature)
);

CREATE TABLE IF NOT EXISTS column_maps (
    profile_id INTEGER NOT NULL REFERENCES column_map_profiles(id) ON DELETE CASCADE,
    source_column TEXT NOT NULL,
    system_field TEXT NOT NULL,
    PRIMARY KEY (profile_id, source_column)
);
