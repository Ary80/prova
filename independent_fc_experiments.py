from config import config_dict
from data_generator import generate_dummy_categorical_dataset
from agents import IndependentFullyConnectedAgents
from evaluation import obtain_metrics


""" Create data """
print("Generating training and testing data")
train_data = generate_dummy_categorical_dataset(config_dict)
test_data = generate_dummy_categorical_dataset(config_dict)

""" Train Agents """
print("Training agents")
ifca = IndependentFullyConnectedAgents(config_dict)
ifca.fit(train_data)
training_stats = ifca.training_stats
obtain_metrics(training_stats)

""" Evaluate Agent Generalisation """
print("Evaluating agents on novel input")
ifca.predict(test_data)
testing_stats = ifca.testing_stats
obtain_metrics(testing_stats)







###############
## Version 2 ##
###############
from config import config_dict
from data_generator import generate_dummy_categorical_dataset
from agents import DenseAgents
from evaluation import obtain_metrics
from networks import DenseListenerPolicyNetwork, DenseSpeakerPolicyNetwork


""" Create data """
print("Generating training and testing data")
train_data = generate_dummy_categorical_dataset(config_dict)
test_data = generate_dummy_categorical_dataset(config_dict)


""" Train Agents """
speaker = DenseSpeakerPolicyNetwork(config_dict)
listener = DenseListenerPolicyNetwork(config_dict)

da = DenseAgents(config_dict,speaker,listener)
da.fit(train_data)
obtain_metrics(da.training_stats)

""" Evaluate Agent Generalisation """
print("Evaluating agents on novel input")
da.predict(test_data)
obtain_metrics(da.testing_stats)









