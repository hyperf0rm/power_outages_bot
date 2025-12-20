CREATE SCHEMA IF NOT EXISTS light_bot;

CREATE TABLE light_bot.users (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id bigint NOT NULL UNIQUE,
    username varchar(32),
    last_message_hash char(32),
    created_at timestamptz DEFAULT now() NOT NULL,
    blocked_at timestamptz
);

CREATE TABLE light_bot.addresses (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES light_bot.users(user_id) ON DELETE CASCADE,
    address varchar(255) NOT NULL,
    created_at timestamptz DEFAULT now() NOT NULL
    UNIQUE (user_id, address)
);
