import cPickle as pickle
from argparse import ArgumentParser
from showdown_client import ShowdownClient, NeuralNetworkAgent

from deepx.nn import *

def parse_args():
    argparser = ArgumentParser()
    argparser.add_argument('team')
    argparser.add_argument('model')

    return argparser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    with open(args.team) as fp:
        team_text = fp.read()

    with open('converter.pkl') as fp:
        converter = pickle.load(fp)

    net = Vector(converter.get_input_dimension()) >> Repeat(Tanh(1000), 2) >> Softmax(converter.get_output_dimension())
    with open(args.model) as fp:
        net.set_state(pickle.load(fp))

    client = ShowdownClient(NeuralNetworkAgent(net, converter))
    client.start()
    client.choose_name('asdf141231232', 'onmabd')
    client.mute()
    client.teambuilder()
    client.create_team(team_text, 'lopunny')
    client.home()

    client.select_battle_format('ou')
    client.play(100)
