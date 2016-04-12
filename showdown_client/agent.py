from showdown_parser import Action, Switch

class Agent(object):

    def get_action(self, gamestate, legal_actions):
        raise NotImplementedError()

class InteractiveAgent(Agent):

    def get_action(self, gamestate, legal_actions, initial=False):
        print "Gamestate: %s" % gamestate
        print "Legal Actions: %s" % legal_actions

        print "Your action?"
        action_string = raw_input(">>> ")
        return Action.from_string(action_string)

class NeuralNetworkAgent(Agent):

    def __init__(self, net, converter):
        self.net = net
        self.converter = converter

    def predict(self, state):

        x = self.converter.encode_state(state)

        probs = self.net.predict(x[None])[0].tolist()
        actions = self.converter.get_actions()

        best = sorted(zip(probs, actions), key=lambda x: -x[0])

        probs, actions = zip(*best)
        return probs, actions

    def get_action(self, state, legal_actions, initial=False):
        probs, actions = self.predict(state)

        print "================================"
        print "Matchup: %s[%.2f] vs %s[%.2f]" % (state.get_primary(0).name,
                                        state.get_health(0),
                                        state.get_primary(1).name,
                                        state.get_health(1))
        print "Legal actions:", legal_actions
        print
        print "My team: %s" % ', '.join(["%s[%.2f]" % ((p.get_name()), p.health) for p in state.get_team(0)[1:]])
        print "Their team: %s" % ', '.join(["%s[%.2f]" % ((p.get_name()), p.health) for p in state.get_team(1)[1:]])
        print
        print
        for i, (prob, action) in enumerate(zip(probs, actions)[:5]):
            print "Prediction[%u]: %s (%.3f)" % (i + 1, action, prob)
        for action in actions:
            if initial and action.is_move():
                return Switch(state.get_primary(0).get_name())
            if action in legal_actions:
                print "Choice:", action
                return action
