using System;
using Accord.Statistics.Models.Markov;
using Accord.Statistics.Distributions.Univariate;

public class Test {
    public static void Main() {
        var hmm = new HiddenMarkovModel<NormalDistribution, double>(2, new NormalDistribution());
        Console.WriteLine("Success!");
    }
}
