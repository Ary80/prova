import random
import numpy as np
import time 
import json

import keras
from keras.models import Sequential, load_model, Model 
from keras.layers.core import Dense, Dropout, Activation, Flatten
from keras.layers import Input, Dense, Convolution2D, LSTM
from keras.optimizers import RMSprop
from keras.layers.normalization import BatchNormalization
from keras import backend as K




class BaseAgents(object):
	"""
	Abstraction of agents
	"""
	def __init__(self, config_dict, speaker, listener, save_training_stats=True, save_testing_stats=True):
		self.config_dict = config_dict
		self.speaker_model = speaker
		self.listener_model = listener
		self.save_training_stats = save_training_stats
		self.save_testing_stats = save_testing_stats
		self.training_stats = []
		self.testing_stats = []
		self.initialize_parameters()

	def initialize_parameters(self):
		""" Assign config parameters to local vars """
		self.max_message_length = self.config_dict['max_message_length']
		self.alphabet = self.config_dict['alphabet']
		self.alphabet_size = self.config_dict['alphabet_size']
		self.speaker_lr = self.config_dict['speaker_lr']
		self.speaker_dim = self.config_dict['speaker_dim']
		self.speaker_input_dim = self.config_dict['speaker_input_dim']
		self.listener_lr = self.config_dict['listener_lr']
		self.listener_dim = self.config_dict['listener_dim']
		self.training_epoch = self.config_dict['training_epoch']
		self.batch_size = self.config_dict['batch_size']
		self.n_classes = self.config_dict['n_distractors'] + 1
		self.n_batches = self.config_dict['n_batches']

	def calculate_reward(self, chosen_target_idx, target_candidate_idx):
		""" Determine reward given indices """
		if target_candidate_idx[chosen_target_idx]==1.:
			return 1
		else:
			return 0

	def sample_from_networks_on_batch(self, target_input, candidates, target_candidate_idx):
		## Sample from speaker
		speaker_message, speaker_probs = self.speaker_model.sample_from_speaker_policy(target_input)
		## Sample from listener
		listener_action, listener_probs = self.listener_model.sample_from_listener_policy(speaker_message, candidates)
		## Calculate reward
		reward = self.calculate_reward(listener_action, target_candidate_idx)
		## Store batch inputs and outputs
		self.speaker_model.remember_speaker_training_details(target_input, speaker_message, speaker_probs, reward)
		self.listener_model.remember_listener_training_details(speaker_message, listener_action, listener_probs, candidates, reward)
		## Increment batch statistics
		self.total_training_reward += reward
		self.batch_counter += 1
		## Record training statistics
		if self.save_training_stats:
			self.training_stats.append({
					"reward": reward,
					"input": target_input,
					"message": speaker_message,
					"chosen_target_idx": listener_action
					})

	def train_networks_on_batch(self):
		""" Train Speaker and Listener network on batch """
		## Train speaker model 
		self.speaker_model.train_speaker_policy_on_batch()
		## Train listener model
		self.listener_model.train_listener_policy_on_batch()
		## Reset batch counter
		self.batch_counter = 0

	def fit(self, train_data):
		""" Random Sampling of messages and candidates for training"""
		self.total_training_reward = 0
		self.batch_counter = 0
		for target_input, candidates, target_candidate_idx in train_data:
			self.sample_from_networks_on_batch(target_input, candidates, target_candidate_idx)
			if self.batch_counter==self.batch_size:
				self.train_networks_on_batch()

	def predict(self, test_data):
		""" Random Sampling of messages and candidates for testing"""
		self.testing_stats = []
		total_reward = 0
		for target_input, candidates, target_candidate_idx in test_data:
			message, message_probs = self.speaker_model.infer_from_speaker_policy(target_input)
			chosen_target_idx = self.listener_model.infer_from_listener_policy(message,candidates)
			reward = self.calculate_reward(chosen_target_idx,target_candidate_idx)
			total_reward += reward

			if self.save_testing_stats:
				self.testing_stats.append({
						"reward": reward,
						"input": target_input,
						"message": message,
						"chosen_target_idx": chosen_target_idx,
						})



class RandomBaselineAgents(BaseAgents):
	"""
	Agents trained on random baseline dataset

	Example
	-------
	from config import random_config_dict as config_dict
	from data_generator import generate_dummy_categorical_dataset
	from networks import RandomBaselineAgents
	from rl.speaker_policy_networks import RandomSpeakerNetwork
	from rl.listener_policy_networks import RandomListenerNetwork
	
	## Get training data
	train_data = generate_dummy_categorical_dataset(config_dict,"training")

	speaker = RandomSpeakerNetwork(config_dict)
	listener = RandomListenerNetwork(config_dict)

	## Initialize and train agent
	rba = RandomBaselineAgents(config_dict, speaker, listener)
	rba.fit(train_data)
	"""
	def __init__(self, config_dict, speaker, listener, save_training_stats=True, save_testing_stats=True):
		super(RandomBaselineAgents, self).__init__(config_dict, speaker, listener, save_training_stats, save_testing_stats)



class VisaAgents(BaseAgents):
	""" 
	Agents for Visa dataset  

	Example:
	--------
	from config import visa_config_dict as config_dict
	from rl.agents import VisaAgents
	from rl.speaker_policy_networks import DenseSpeakerNetwork
	from rl.listener_policy_networks import DenseListenerNetwork
	from visa_wrapper import VisaDatasetWrapper 

	print("Get dataset")
	data_generator = VisaDatasetWrapper()
	data_generator.create_train_test_datasets(config_dict)

	print("Train Agents")
	speaker = DenseSpeakerNetwork(config_dict)
	listener = DenseListenerNetwork(config_dict)
	da = VisaAgents(config_dict,speaker,listener)
	da.fit(data_generator)
	"""
	def __init__(self, config_dict, speaker, listener, save_training_stats=True, save_testing_stats=True, verbose=True):
		super(VisaAgents, self).__init__(config_dict, speaker, listener, save_training_stats, save_testing_stats)
		self.verbose = verbose

	def fit(self, data_generator):
		""" Override fit method to use data_generator """
		self.total_training_reward = 0
		self.batch_counter = 0

		for n in range(self.n_batches):
			if self.verbose:
				print("Batch: %s of %s"%(n,self.n_batches))
			batch = data_generator.training_batch_generator()
			for b in batch:
				target_input, candidates, target_candidate_idx = b
				self.sample_from_networks_on_batch(target_input, candidates, target_candidate_idx)
				if self.batch_counter==self.batch_size:
					self.train_networks_on_batch()

	def evaluate_on_training_set(self, data_generator):
		""" Determine performance on training set """
		self.training_eval_stats = []
		total_reward = 0
		training_eval_set = data_generator.training_set_evaluation_generator()
		training_size = data_generator.n_training_rows
		for i,train_example in enumerate(training_eval_set):
			if self.verbose:
				print("Training Example: %s of %s"%(i+1,training_size))
			target_input, candidates, target_candidate_idx = train_example
			message, message_probs = self.speaker_model.infer_from_speaker_policy(target_input)
			chosen_target_idx, listener_probs = self.listener_model.infer_from_listener_policy(message, candidates)
			reward = self.calculate_reward(chosen_target_idx,target_candidate_idx)
			total_reward += reward

			if self.save_training_stats:
				self.training_eval_stats.append({
						"reward": reward,
						"input": target_input,
						"message": message,
						"chosen_target_idx": chosen_target_idx,
						})

	def predict(self, data_generator):
		""" Determine performance on training set """
		self.testing_stats = []
		total_reward = 0
		test_set = data_generator.testing_set_generator()
		test_size = data_generator.n_testing_rows
		for i,test_example in enumerate(test_set):
			if self.verbose:
				print("Test Example: %s of %s"%(i+1,test_size))
			target_input, candidates, target_candidate_idx = test_example
			message, message_probs = self.speaker_model.infer_from_speaker_policy(target_input)
			chosen_target_idx, listener_probs = self.listener_model.infer_from_listener_policy(message, candidates)
			reward = self.calculate_reward(chosen_target_idx,target_candidate_idx)
			total_reward += reward

			if self.save_testing_stats:
				self.testing_stats.append({
						"reward": reward,
						"input": target_input,
						"message": message,
						"chosen_target_idx": chosen_target_idx,
						})


