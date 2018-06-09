import pandas as pd
import numpy as np
import matplotlib as plt
import matplotlib.image as mpimg

from scipy.ndimage import gaussian_filter1d
import data.sets.urban.stanford_campus_dataset.scripts.coordinate_transformations as ct
import data.sets.urban.stanford_campus_dataset.scripts.post_processing as pproc

THRESHOLD = 200
HEADING_STEP = 10
FRAME_RATE = 30


class Object(object):
    def __init__(self, id, label):
        self.neighbors = {}
        self.trajectory = {}
        self.exist = {}
        self.time = {}
        self.heading = {}
        self.type = label
        self.frame_counter = 0
        self.id = id

    def update(self, data, frame):
        agents = np.array([data[:, 0], (data[:, 3] + data[:, 1]) / 2, (data[:, 2] + data[:, 4]) / 2]).T
        idx = self.id == data[:, 0]
        self.trajectory[frame] = agents[idx, 1:3]
        self.time[frame] = frame / FRAME_RATE
        others = np.delete(agents, np.where(idx)[0][0], 0)

        vectors_to_others = others[:, 1:3] - self.trajectory[frame]
        distances = np.linalg.norm(vectors_to_others.astype(float), axis=1)
        self.neighbors[frame] = np.hstack((vectors_to_others[distances < THRESHOLD], others[distances < THRESHOLD]))[:, 0:3]
        self.get_headings(frame)
        self.exist[frame] = False if data[idx, 6] == 1 else True


    def get_headings(self, frame):
        if self.frame_counter % HEADING_STEP == 0 and self.frame_counter != 0:
            heading = self.trajectory[frame] - self.trajectory[frame - HEADING_STEP]
            for i in range(0, HEADING_STEP):
                self.heading[frame - i] = heading
            try:
                self.heading[list(self.trajectory.keys())[0]]
            except KeyError:
                self.heading[list(self.trajectory.keys())[0]] = self.heading[list(self.trajectory.keys())[1]]
        elif self.frame_counter == len(self.trajectory.keys()):
            last_key_in_heading = self.heading.keys()[-1]
            last_key_in_traj = self.trajectory.keys()[-1]
            for i in range(last_key_in_heading + 1, last_key_in_traj + 1):
                self.heading[i] = self.heading[-1]
            assert (self.heading.keys() == self.trajectory.keys())
        self.frame_counter += 1


class Route(object):
    def __init__(self, start, end):
        x = np.array([start[0], end[0]])
        y = np.array([start[1], end[1]])
        self.interp(x, y)
        self.path = np.column_stack([self.x_fit, self.y_fit])

    def interp(self, x, y):
        t = np.linspace(0, 1, len(x))
        t2 = np.linspace(0, 1, 100)

        x2 = np.interp(t2, t, x)
        y2 = np.interp(t2, t, y)
        sigma = 5
        x3 = gaussian_filter1d(x2, sigma)
        y3 = gaussian_filter1d(y2, sigma)

        x4 = np.interp(t, t2, x3)
        y4 = np.interp(t, t2, y3)

        self.x_fit = x3
        self.y_fit = y3


class Loader(object):
    def __init__(self, path, reload=False):
        self.path = path
        self.df = {}
        self.frame_dict = {}
        self.obj_dict = {}
        if reload:
            self.load_data()
            self.make_dicts()
        else:
            self.load_dicts()
        self.map = mpimg.imread(self.path + "reference.jpg")
        self.obj_route_dict = {}
        self.route_poses = []

    def make_dicts(self):
        # make obj and frame dict
        self.get_relations()

        # store the dicts
        np.save(self.path + 'obj_dict.npy', self.obj_dict)
        np.save(self.path + 'frame_dict.npy', self.frame_dict)
        return True

    def load_dicts(self):
        self.frame_dict = np.load(self.path + 'frame_dict.npy').item()
        self.obj_dict = np.load(self.path + 'obj_dict.npy').item()
        return True

    def load_data(self):
        self.df = pd.read_csv(self.path + "annotations.txt", delim_whitespace=True)
        self.df.columns = ["Track_ID", "xmin", "ymin", "xmax", "ymax", "frame", "lost", "occluded", "generated", "label"]

    def get_relations(self):
        self.frame_dict = {k: np.array(v) for k, v in self.df.groupby('frame')}
        all_IDs = np.unique(self.df["Track_ID"])
        self.obj_dict = {key: Object(key, self.df.loc[self.df["Track_ID"] == key].values[:, 9][0]) for key in all_IDs}
        for frame, data in sorted(self.frame_dict.items()):
            for id in data[:, 0]:
                self.obj_dict[id].update(data, frame)

    def make_obj_dict_by_route(self, route, filter_label=False, label=""):
        self.obj_route_dict = {} # can be called multiple times
        self.route_poses = route.path
        if bool(self.obj_dict):
            for id, data in list(self.obj_dict.items()):
                trajectory = np.squeeze(np.asarray(list(data.trajectory.values())))
                exist = np.squeeze(np.asarray(list(data.exist.values())))
                if np.linalg.norm(trajectory[0] - self.route_poses[0]) < THRESHOLD and np.linalg.norm(
                        trajectory[-1] - self.route_poses[-1]) < THRESHOLD:
                    if not filter_label:
                        self.obj_route_dict[id] = trajectory[exist==True]
                    elif filter_label and data.type == label:
                        self.obj_route_dict[id] = trajectory[exist==True]
            return True
        else:
            print('call load or make dicts')
            return False

    def make_obj_grid_dict(self, id_list, filter_label=False, label=""):
        self.obj_grid_dict = {}

        for id in id_list:
            grid_series = []
            all_frames = list(self.obj_dict[id].heading.keys())
            print(all_frames)
            for frame in all_frames:
                neigbors = self.obj_dict[id].neighbors[frame]#[:, 0:2]
                neigbors_series_filtered_by_type = []
                for neighbor in neigbors:
                    if filter_label:
                        id_neigbor = neighbor[2]
                        if self.obj_dict[id_neigbor].type == label:
                            neigbors_series_filtered_by_type.append(neighbor[0:2])
                    else:
                        neigbors_series_filtered_by_type.append(neighbor[0:2])
                neigbors_series_filtered_by_type = np.asarray(neigbors_series_filtered_by_type)

                heading = self.obj_dict[id].heading[frame]
                if heading.all() != 0:
                    grid = get_grid_cell(neigbors_series_filtered_by_type, heading)
                    grid_series.append(grid)
                else:
                    grid_series.append(np.array([THRESHOLD, THRESHOLD, THRESHOLD]))
            self.obj_grid_dict[id] = grid_series

def filter_by_label(df, label):
    return df.loc[df['label'] == label]


def get_least_projection_neigbor(b, ac, angle_max):
    min_distance = 1234
    least_projection_neigbor = None
    if b is not None and b.shape[0] > 0:
        for idx, neigbor in enumerate(b):
            theta1, d1 = ct.theta1_d1_from_location(neigbor, ac)
            if d1 < min_distance and np.abs(theta1) < angle_max:
                min_distance = d1
                least_projection_neigbor = neigbor
        return least_projection_neigbor, min_distance
    else:
        return None, None


def get_closest_neigbor(a, b, ac, angle_max):
    if b is not None and b.shape[0] > 0:
        idx_closest_neighbor = np.argmin(np.linalg.norm(np.array(b, dtype=np.float32), axis=1))
        closest_neighbor = b[idx_closest_neighbor]
        closest_distance = np.linalg.norm(closest_neighbor)

        theta1, d1 = ct.theta1_d1_from_location(closest_neighbor, ac)

        if np.abs(theta1) < angle_max:
            return closest_neighbor, closest_distance, idx_closest_neighbor, theta1
        elif np.abs(theta1) >= angle_max and b.shape[0] > 1:
            b = np.delete(b, idx_closest_neighbor, axis=0)
            return get_closest_neigbor(a, b, ac, angle_max)
        else:
            return np.array([]), 0, None, 0
    else:
        return np.array([]), 0, None, 0


def get_predecessing_neigbor(b, ac, angle_max):
    min_distance = 1234
    predecessing_neigbor = None
    if b is not None and b.shape[0] > 0:
        for idx, neigbor in enumerate(b):
            theta1, d1 = ct.theta1_d1_from_location(neigbor, ac)

            if np.abs(theta1) < angle_max and np.abs(d1) < min_distance:
                min_distance = d1
                predecessing_neigbor = neigbor

    return predecessing_neigbor, min_distance


def get_grid_cell(neighbors_in_frame, heading):
    n_cells = 7
    xs = np.ones(n_cells)*THRESHOLD

    for n in neighbors_in_frame:
        theta1, d1 = ct.theta1_d1_from_location(n, heading)
        if np.abs(theta1) < np.pi/2:
            idx_grid = ct.polar_coordinate_to_grid_cell(theta1, d1, THRESHOLD, np.pi, n_cells, 1)
            if d1 < xs[idx_grid]:
                xs[idx_grid] = d1

    return xs



if __name__ == "__main__":
    path = "../annotations/hyang/video0/"
    video = '../videos/hyang/video0/video.mov'
    loader = Loader(path)
