data {
    int<lower=0> Ss; // number of seconds
    int<lower=0> Us; // number of users
    int<lower=0> Ds; // number of dates

    real secs[Ss];

    int<lower=1,upper=Us> uids[Ss];
    int<lower=1,upper=7> dows[Ss];
    int<lower=1,upper=Ds> dates[Ss];
    int<lower=1,upper=Ds> nth[Ss];
}

transformed data {
    int<lower=0,upper=1> is_sat[Ss];
    real<lower=0> corrected_secs[Ss];
    int<lower=1,upper=Ds> beginner_nth[Ss];

    for (j in 1:Ss) is_sat[j] = (dows[j] == 7 ? 1 : 0);
    for (j in 1:Ss) corrected_secs[j] = (secs[j] < 0 ? 300 : secs[j]);
    for (j in 1:Ss) beginner_nth[j] = (nth[j] < 60 ? nth[j] : 60);
}

parameters {
    real<lower=0> mu;
    real<lower=0> sigma;

    vector[Us] skill_effect;
    real<lower=0> skill_dev;

    vector[Ds] date_effect;
    real<lower=0> date_dev;

    real sat_effect;
}

transformed parameters {
    real beginner_gain = 0.2;
    real beginner_decay = 14;

    vector[Ds] nth_effect;
    for (j in 1:Ds)
    nth_effect[j] = beginner_gain * exp(-j / beginner_decay);
}

model {
    // Priors
    skill_effect ~ normal(0, skill_dev);
    date_effect ~ normal(0, date_dev);

    // Model
    corrected_secs ~
      lognormal( mu
               + skill_effect[uids]
               //+ improvement_rate[uids] *. to_vector(nth)
               + nth_effect[nth]
               + date_effect[dates]
               + sat_effect * to_vector(is_sat),
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
