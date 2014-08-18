drop table if exists login_history;
create table login_history (
  id text primary key,
  day_name text not null,
  hour integer not null,
  num_logins integer not null
);

drop table if exists history_outliers;
create table history_outliers (
  id text primary key,
  reason text
);

drop table if exists prediction_outliers;
create table prediction_outliers (
  id text primary key,
  multiplier real not null,
  reason text
);

drop table if exists login_predictions;
create table login_predictions (
  id text primary key,
  num_logins real not null
);