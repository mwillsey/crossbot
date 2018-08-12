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
    real<lower=0> log_secs[Ss];

    for (j in 1:Ss) is_sat[j] = (dows[j] == 7 ? 1 : 0);
    for (j in 1:Ss) log_secs[j] = log(secs[j] < 0 || secs[j] > 300 ? 300 : secs[j]);
}

parameters {
    real<lower=0> mu;
    real<lower=0> sigma;

    vector[Us] skill_effect;
    real<lower=0> skill_dev;

    vector[Ds] date_effect;
    real<lower=0> date_dev;

    real sat_effect;
    real beginner_gain;
    real<lower=0> beginner_decay;
}

transformed parameters {
    vector[Ds] nth_effect;
    vector[Ss] predictions;

    for (j in 1:Ds)
    nth_effect[j] = beginner_gain * exp(-j / beginner_decay);

    predictions = mu
                + skill_effect[uids]
                + nth_effect[nth]
                + date_effect[dates]
                + sat_effect * to_vector(is_sat);
}

model {
    // Priors
    skill_effect ~ normal(0, skill_dev);
    date_effect ~ normal(0, date_dev);

    // Model
    log_secs ~ normal(predictions, sigma);
}

generated quantities {
    vector[Ss] residuals;
    for (j in 1:Ss) residuals[j] = (log_secs[j] - predictions[j]) / sigma;
}
