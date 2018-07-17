data {
    int<lower=0> Ss; // number of seconds
    int<lower=0> Us; // number of users
    int<lower=0> Ds; // number of dates

    real<lower=0> secs[Ss];

    int<lower=1,upper=Us> uids[Ss];
    int<lower=1,upper=7> dows[Ss];
    int<lower=1,upper=Ds> dates[Ss];
    real ago[Ss];
}

parameters {
    real<lower=0> mu;
    real<lower=0> sigma;

    real skill_effect[Us];
    real<lower=0> skill_dev;

    real date_effect[Ds];
    real<lower=0> date_dev;

    real sat_effect;

    real improvement_rate[Us];
    real improvement_dev;
}

model {
    // Priors
    skill_effect ~ normal(0, skill_dev);
    date_effect ~ normal(0, date_dev);
    improvement_rate ~ normal(0, improvement_dev);

    // Model
    for (j in 1:Ss)
    secs[j] ~ lognormal(mu + skill_effect[uids[j]] +
                        (improvement_rate[uids[j]] * ago[j]) +
                        date_effect[dates[j]] +
                        (dows[j] == 7 ? sat_effect : 0),
                        sigma);
}

generated quantities {
    real avg_time;
    real avg_skill[Us];
    real avg_date[Ds];
    real avg_sat;

    avg_time = exp(mu);
    for (j in 1:Us) avg_skill[j] = exp(skill_effect[j]);
    for (j in 1:Ds) avg_date[j] = exp(date_effect[j]);
    avg_sat = exp(sat_effect);
}
