import sys
import numpy as np
import random
import datetime

from Game import Game
from Qtable import Qtable


PATH = "qtables/"
# total_episodes = 500000        # Total episodes
# learning_rate = 0.8           # Learning rate
max_steps = 20  # Max steps per episode
# gamma = 0.95                  # Discounting rate

# Exploration parameters
epsilon = 1.0  # Exploration rate
max_epsilon = 1.0  # Exploration probability at start
min_epsilon = 0.1  # Minimum exploration probability


# decay_rate = 0.004             # Exponential decay rate for exploration prob


class QRL:
    def __init__(self, total_episodes, learning_rate, discount_rate, decay_rate):
        self.total_episodes = total_episodes
        self.learning_rate = learning_rate
        self.discount_rate = discount_rate
        self.epsilon = 1.0
        self.max_epsilon = 1.0
        self.min_epsilon = 0.05
        self.decay_rate = decay_rate

        self.qtable = Qtable(4, 64, max_steps+1)
        self.environment = Game(map_name="8x8", is_slippery=False, max_steps=max_steps)

        print("Initialized QRL with Parameters: %i, %.2f, %.2f, %.4f" % (total_episodes, learning_rate, discount_rate, decay_rate))
        self.exportPath = None

        self.statistics = {bytes((i, j)): [0, 0, 0, 0] for i in range(self.environment.observation_space.n//max_steps) for j in range(max_steps)}
        self.expexpratio = [0, 0]

    def statusBar(self, iteration):
        bar_len = 60
        filled_len = int(round(bar_len * iteration / self.total_episodes))
        percents = 100 * iteration / self.total_episodes
        bar = '=' * filled_len + '-' * (bar_len - filled_len)
        sys.stdout.write('\r[%s] %s%%\n' % (bar, percents))
        sys.stdout.flush()

    def exportToFile(self):
        date = datetime.datetime.today().strftime("%y%m%d_%H")
        path = PATH + date
        self.exportPath = path
        print("Storing Q-Table in %s.pkl... " % self.exportPath)
        self.qtable.toFile(path)

    def loadFromFile(self, path=None):
        if path is None:
            path = self.exportPath
        print("Loading Q-Table from %s.pkl" % path)
        self.qtable.fromFile(path)

    def updateQ(self, state, action, new_state, reward, done):
        #if new_state not in self.qtable:
        #    self.qtable[new_state] = np.zeros(self.environment.action_space.n)

        # if state is unknown, add empty entry to qtable
        #if state not in self.qtable:
        #    self.qtable[state] = np.zeros(self.environment.action_space.n)

        if done:
            self.qtable.update(state, action, reward)

        # Update Q(s,a):= Q(s,a) + lr [R(s,a) + gamma * max Q(s',a') - Q(s,a)]
        # qtable[new_state,:] : all the actions we can take from new state
        oldValue = self.qtable.get(state, action)
        newValue = oldValue + self.learning_rate * (reward + self.discount_rate * np.max(self.qtable.get(new_state)) - oldValue)
        self.qtable.update(state, action, newValue)

    def updateEpsilon(self, episode):
        self.epsilon = self.min_epsilon + (self.max_epsilon - self.min_epsilon) * np.exp(-self.decay_rate * episode)

    def learnFromSteps(self, list_of_steps):
        # iterate through all steps taken by the agent from last to first and learn
        for step in list_of_steps:
            # update qtable-entry for current state and action
            self.updateQ(*step)

    def run(self):
        # execute Game and learn
        for episode in range(self.total_episodes):
            # display progress bar
            if episode % (self.total_episodes/100) == 0:
                pass #self.statusBar(episode)

            # Reset the environment
            state = self.environment.reset()

            # execute one iteration of the game
            steps = []
            done = False
            while not done and len(steps) < max_steps:
                action = self.getNextAction(state)
                new_state, reward, done, p = self.environment.step(action)
                steps.append((state, action, new_state, reward, done))
                self.statistics[state][action] += 1

                state = new_state

            # iterate through all steps taken by the agent from last to first and learn
            self.learnFromSteps(steps)

            # Reduce epsilon
            self.updateEpsilon(episode)

        self.exportToFile()

    def getNextAction(self, state, test=False):
        if test:
            exp_exp_tradeoff = self.epsilon+1
        else:
            exp_exp_tradeoff = random.uniform(0, 1)

        if exp_exp_tradeoff > self.epsilon:
            self.expexpratio[0] += 1
            # exploit
            if np.max(self.qtable.get(state)) == 0:
                actions = []
                for step in range(max_steps):
                    actions.append(np.argmax(self.qtable.get(bytes((state[0], step)))))
                unique, counts = np.unique(actions, return_counts=True)

                action = np.argmax(counts)
            else:
                actions = np.where(self.qtable.get(state) == np.max(self.qtable.get(state)))[0]
                action = random.choice(actions)
        else:
            self.expexpratio[1] += 1
            # explore
            action = self.environment.action_space.sample()

        return action

    def test(self, render=True):
        # Reset the environment
        # execute one iteration of the game
        steps = []
        done = False
        state = self.environment.reset()
        while not done and max_steps > len(steps):
            if render:
                self.environment.render("human")
            action = self.getNextAction(state, True)
            new_state, reward, done, p = self.environment.step(action)
            steps.append((state, action, new_state, reward))
            state = new_state

        return steps
