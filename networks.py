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


class BasePolicyModel(object):
	""" Parent model with save and load methods """
	def __init__(self):
		self._model = None
		self._config_dict = None
		self.load_config()

	def load_config(self):
		assert self._config_dict is not None. "Please pass in the config dictionary"
		self._max_message_length = self.config_dict['max_message_length']
		self._alphabet = self.config_dict['alphabet']
		self._alphabet_size = self.config_dict['alphabet_size']
		self._speaker_lr = self.config_dict['speaker_lr']
		self._speaker_dim = self.config_dict['speaker_dim']
		self._listener_lr = self.config_dict['listener_lr']
		self._listener_dim = self.config_dict['listener_dim']
		self._training_epoch = self.config_dict['training_epoch']
		self._batch_size = self.config_dict['batch_size']
		self._n_classes = self.config_dict['n_distractors'] + 1

	def save(self, weights_file, params_file):
		pass

	def save_weights(self, file_path):
		pass

	def save_params(self, file_path):
		pass

	@classmethod
	def load_params(cls, file_path):
		pass

	@classmethod
	def load(cls, weights_file, params_file):
		pass





class SpeakerPolicy(BasePolicyModel):
	""" Parent speaker policy model """
	def __inti__(self, model, config_dict):
		super(BasePolicyModel).__init__()
		self._model = model
		self._config_dict = config_dict
		
	def sample_speaker_policy(self, target_input):
		""" Stochastically sample message of length self.max_message_length from speaker policy """ 
		x = target_input.reshape([1, self.speaker_dim, 1])
		probs = self._model.predict(x, batch_size=1)
		normalized_probs = probs/np.sum(probs)

		message = ""
		message_probs = []
		for i in range(self.max_message_length):
			sampled_symbol = np.random.choice(self.alphabet_size, 1, p=normalized_probs[0])[0]
			message += str(sampled_symbol) + "#"
			message_probs.append(normalized_probs[0][sampled_symbol])
		
		## TODO: Also return sum[log prob () mi | target input and weights)]??
		return message, message_probs

	def train_on_batch(self, reward):
		pass

	def infer_speaker_policy(self):
		pass








class IndependentFullyConnectedAgents(object):
	"""
	Two independent agents which use fully connected neural networks and 
	jointly optimize given only the reward

	Example
	-------
	from config import config_dict
	from data_generator import generate_dummy_data
	from networks import RandomAgent
	
	## Get training data
	train_data = generate_dummy_data()

	## Initialize and train agent
	ifca = IndependentFullyConnectedAgents(config_dict)
	ifca.fit(train_data)
	"""
	def __init__(self, config_dict, save_training_stats=True, save_testing_stats=True):
		self.config_dict = config_dict
		self.save_training_stats = save_training_stats
		self.save_testing_stats = save_testing_stats
		self.training_stats = None
		self.testing_stats = None
		self.initialize_parameters()
		self.initialize_speaker_model()

	def initialize_parameters(self):
		""" Assign config parameters to local vars """
		self.max_message_length = self.config_dict['max_message_length']
		self.alphabet = self.config_dict['alphabet']
		self.alphabet_size = self.config_dict['alphabet_size']
		self.speaker_lr = self.config_dict['speaker_lr']
		self.speaker_dim = self.config_dict['speaker_dim']
		self.listener_lr = self.config_dict['listener_lr']
		self.listener_dim = self.config_dict['listener_dim']
		self.training_epoch = self.config_dict['training_epoch']
		self.batch_size = self.config_dict['batch_size']
		self.n_classes = self.config_dict['n_distractors'] + 1

	def initialize_speaker_model(self):
		""" 2 Layer fully-connected neural network """
		self.speaker_model = Sequential()
		self.speaker_model.add(Dense(self.speaker_dim, activation="relu", input_shape=(self.speaker_dim,)))
		self.speaker_model.add(Dense(self.alphabet_size,activation="softmax"))
		self.speaker_model.compile(loss="categorical_crossentropy", optimizer=RMSprop(lr=self.speaker_lr))

	def initialize_listener_model(self):
		""" 2 Layer fully-connected neural network """
		self.listener_model = Sequential()
		self.listener_model.add(Dense(self.listener_dim, activation="relu", input_shape=(self.listener_dim,)))
		self.listener_model.add(Dense(self.n_classes,activation="softmax"))
		self.listener_model.compile(loss="categorical_crossentropy", optimizer=RMSprop(lr=self.listener_lr))

	def sample_speaker_policy_for_message(self,target_input):
		""" Stochastically sample message of length self.max_message_length from speaker policy """ 
		probs = self.speaker_model.predict(target_input.reshape([1,self.speaker_dim,1]),batch_size=1)
		normalized_probs = probs/np.sum(probs)

		message = ""
		message_probs = []
		for i in range(self.max_message_length):
			sampled_symbol = np.random.choice(self.alphabet_size, 1, p=normalized_probs[0])[0]
			message += str(sampled_symbol) + "#"
			message_probs.append(normalized_probs[0][sampled_symbol])
		
		## TODO: Also return sum[log prob () mi | target input and weights)]??
		return message, message_probs

	def train_speaker_policy_on_batch(self, target_inputs, message_probs, rewards):
		""" Update speaker policy given rewards """
		self.m_probs = np.vstack(message_probs)
		self.r = np.vstack(rewards)
		self.X = np.squeeze(np.vstack(target_inputs))
		self.Y = self.r.flatten() * np.sum(self.m_probs,axis=1) 
		print("X.shape: %s , Y.shape: %s"%(self.X.shape,self.Y.shape))

		self.X_ = self.X.reshape([self.batch_size,self.speaker_dim,1])
		#self.Y_ = self.Y.reshape([self.batch_size,1])

		self.speaker_model.train_on_batch(self.X_, self.Y)
		print("Batch training complete")

	def infer_from_speaker_policy(self,target_input):
		""" Greedily obtain message from speaker policy """
		## Get symbol probabilities given target input
		probs = self.speaker_model.predict(target_input.reshape([1,self.speaker_dim,1]),batch_size=1)
		normalized_probs = probs/np.sum(probs)

		## Greedy get symbols with largest probabilities
		argmax_indices = list(normalized_probs[0].argsort()[-self.max_message_length:][::-1])
		message_probs = normalized_probs[0][argmax_indices]
		message = "#".join([str(e) for e in list(argmax_indices)])
		
		## TODO: Also return sum[log prob () mi | target input and weights)]??
		return message, message_probs

	def listener_policy(self,message,candidates):
		""" Randomly choose a target """
		return np.random.randint(len(candidates))

	def calculate_reward(self, chosen_target_idx, target_candidate_idx):
		""" Determine reward given indices """
		if chosen_target_idx==target_candidate_idx:
			return 1
		else:
			return 0

	def store_past(self):
		pass

	def train_agents_on_batch(self):
		pass

	def fit(self, train_data):
		""" Random Sampling of messages and candidates for training"""
		self.training_stats = []
		message_probs_storage = []
		rewards_storage = []

		total_reward = 0
		batch_counter = 0
		batch_training_inputs = []
		for target_input, candidates, target_candidate_idx in train_data:
			message, message_probs = self.sample_speaker_policy_for_message(target_input)
			print("Message: %s, Probs: %s"%(message,message_probs))

			chosen_target_idx = self.listener_policy(message, candidates)
			reward = self.calculate_reward(chosen_target_idx,target_candidate_idx)
			total_reward += reward
			batch_counter += 1

			## Storage for training
			batch_training_inputs.append(target_input)
			rewards_storage.append(reward)
			message_probs_storage.append(message_probs)

			if self.save_training_stats:
				self.training_stats.append({
											"reward": reward,
											"input": target_input,
											"message": message,
											"chosen_target": candidates[chosen_target_idx]
											})

			if batch_counter==self.batch_size:
				self.train_speaker_policy_on_batch(batch_training_inputs, message_probs_storage, rewards_storage)
				batch_counter = 0
				batch_training_inputs,  message_probs_storage, rewards_storage = [], [], []

	def predict(self,test_data):
		""" Random Sampling of messages and candidates for testing"""
		self.testing_stats = []
		total_reward = 0
		for target_input, candidates, target_candidate_idx in test_data:
			message, message_probs = self.infer_from_speaker_policy(target_input)

			print("Message: %s, Probs: %s"%(message,message_probs))

			chosen_target_idx = self.listener_policy(message,candidates)
			reward = self.calculate_reward(chosen_target_idx,target_candidate_idx)
			total_reward += reward

			if self.save_training_stats:
				self.testing_stats.append({
											"reward": reward,
											"input": target_input,
											"message": message,
											"chosen_target": candidates[chosen_target_idx]
											})




# T = Input(shape=[50])
# t = Dense(50, activation="relu", kernel_initializer="he_normal")(t)
# # t = BatchNormalization()(t)
# t = LSTM(50,return_sequences=False,input_shape=(50,))(t)
# m = Dense(alphabet_size, activation="linear", kernel_initializer="zero")(t)
# model = Model(T,m)
# model.compile(loss="mse",optimizer=RMSprop(lr=0.0001))


"""
Speaker policy network
t => MLP => t_dense => LSTM => m
"""
