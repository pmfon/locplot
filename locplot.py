#!/usr/bin/env python3 

from urllib.parse import urlparse
import subprocess
import sys
import argparse
import tempfile
import os
import json
from collections import defaultdict
import plotly.offline as py
import plotly.graph_objs as go


N_RELEASES = 52


def is_url(url):
    return urlparse(url).scheme != ''

def is_git_repository(path):
    return os.path.isdir(os.path.join(path, '.git'))

def sh(cmd, path=None):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, cwd=path)
    if result.returncode != 0:
        sys.exit('Error executing ` ' + ' '.join(cmd) + '`')
    return result.stdout.decode('utf-8')

def git(tail, path=None):
    cmd = ['git'] + tail
    return sh(cmd, path)

def bootstrap(repository):
    if is_url(repository):
        path = tempfile.mkdtemp()
        git(['clone', repository, path])
    elif is_git_repository(repository):
        path = repository
        if len(git(['status', '-s'], path)) > 0:
            sys.exit('Found uncommitted changes!')    
    else: 
        sys.exit('Can\'t find git repository!')
    
    git(['fetch', '--tags'], path)
    current_branch = git(['symbolic-ref', '--short', 'HEAD'], path).strip()
    return path, current_branch

def get_tags(path):
    result = git(['tag', '--sort', 'v:refname'], path)
    tags = result.split()[-N_RELEASES:]
    return tags

def get_loc(tag, path, exclude):
    git(['checkout', tag], path)
    git(['clean', '-fdq'], path)

    cmd = ['tokei', '--output', 'json']
    if exclude:
        for e in exclude:
            cmd.append('--exclude')
            cmd.append(e)

    result = sh(cmd, path)
    return json.loads(result)

def generate_stats(path, exclude):
    tags = get_tags(path)

    stats = defaultdict(lambda: defaultdict(list))
    for tag in tags:
        tmp_stats = get_loc(tag, path, exclude)    
        for language, count in tmp_stats.items():
            stats[language]['x'].append(tag)
            stats[language]['y'].append(count['code'])
            if count['comments'] > 0:
                stats['Comments']['x'].append(tag)
                stats['Comments']['y'].append(count['comments'])
    return stats

def plot(stats, filename=None):
    bars = []
    for language, data in stats.items():
        bar = go.Bar(
            x = data['x'],
            y = data['y'],
            name = language,
            width = 1)
        bars.append(bar)
    layout = go.Layout(
        barmode ='stack'
    )

    figure = go.Figure(data=bars, layout=layout)
    if filename is None: 
        filename = 'loc.html'
    py.plot(figure, filename=filename)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('repository', help='a git repository')
    parser.add_argument('--output', metavar='file', help='write the results to <file>. Defaults to "loc.html"')
    parser.add_argument('--exclude', type=str, action='append', metavar='glob_expression', help='ignore matching files')
    args = parser.parse_args()

    path, branch = bootstrap(args.repository)

    try:        
        stats = generate_stats(path, args.exclude)
        plot(stats, args.output)
    except Exception as e:
        print(e)
    finally:
         git(['checkout', branch], path)

if __name__ == '__main__':
    main()














