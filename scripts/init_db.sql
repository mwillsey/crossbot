
CREATE TABLE IF NOT EXISTS
crossword_time(
  userid   TEXT NOT NULL,
  date     INTEGER NOT NULL,
  seconds  INTEGER NOT NULL,
  UNIQUE(userid, date)
);
