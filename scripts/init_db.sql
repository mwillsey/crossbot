
CREATE TABLE IF NOT EXISTS
crossword_time(
  userid   TEXT NOT NULL,
  date     INTEGER NOT NULL,
  seconds  INTEGER NOT NULL,
  timestamp DATETIME;
  UNIQUE(userid, date)
);

CREATE TABLE IF NOT EXISTS
mini_crossword_time(
  userid   TEXT NOT NULL,
  date     INTEGER NOT NULL,
  seconds  INTEGER NOT NULL,
  timestamp DATETIME;
  UNIQUE(userid, date)
);

CREATE TABLE IF NOT EXISTS
easy_sudoku_time(
  userid   TEXT NOT NULL,
  date     INTEGER NOT NULL,
  seconds  INTEGER NOT NULL,
  timestamp DATETIME;
  UNIQUE(userid, date)
);

CREATE TABLE IF NOT EXISTS
query_shorthands(
  name      TEXT NOT NULL,
  command   TEXT NOT NULL,
  userid    TEXT NOT NULL,
  timestamp TEXT NOT NULL;
  UNIQUE(name)
);
