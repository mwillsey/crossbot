data {
    int<lower=0> Ss; // number of seconds
    int<lower=0> Us; // number of users
    int<lower=0> Ds; // number of dates

    real secs[Ss];

    int<lower=1,upper=Us> uids[Ss];
    int<lower=1,upper=7> dows[Ss];
    int<lower=1,upper=Ds> dates[Ss];
    real ago[Ss];
}

transformed data {
    vector[Ss] is_sat;
    for (j in 1:Ss) is_sat[j] = (dows[j] == 7 ? 1.0 : 0.0);

    real<lower=0> corrected_secs[Ss];
    for (j in 1:Ss) corrected_secs[j] = (secs[j] < 0 ? 300 : secs[j]);
}

parameters {
    real<lower=0> mu;
    real<lower=0> sigma;

    vector[Us] skill_effect;
    real<lower=0> skill_dev;

    vector[Ds] date_effect;
    real<lower=0> date_dev;

    real sat_effect;

    vector[Us] improvement_rate;
    real improvement_mu;
    real<lower=0> improvement_dev;
}

model {
    // Priors
    skill_effect ~ normal(0, skill_dev);
    date_effect ~ normal(0, date_dev);
    improvement_rate ~ normal(improvement_mu, improvement_dev);

    // Model
    corrected_secs ~
      lognormal( mu
               + skill_effect[uids]
               + improvement_rate[uids] .* to_vector(ago)
               + date_effect[dates]
               + sat_effect * is_sat,
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
