import numpy as np
import pandas as pd
from collections import defaultdict
import warnings
import copy
import time
import os
srt_time = time.time()
warnings.filterwarnings('ignore')


class UnitSelection:
    def __init__(self, data, flag=False, id=0, method=1, day_coff=10, gap_coff=10, pr_coff=10):
        self.dt = data
        self.base_table = np.zeros(shape=(6, 6))
        self.df_matrix = pd.DataFrame()
        self.c = 0
        self.df_matrix_course = pd.DataFrame()
        self.flag = flag
        self.id = id
        self.method = method

        # اگر متد 2 انتخاب شده باشد، مقادیر پیش‌فرض استفاده می‌شوند
        if method == 2:
            self.day_coff = day_coff or 10
            self.gap_coff = gap_coff or 10
            self.pr_coff = pr_coff or 10
        else:
            self.day_coff, self.gap_coff, self.pr_coff = 10, 10, 10

        self.select_method(method=method, day_coff=self.day_coff, gap_coff=self.gap_coff, pr_coff=self.pr_coff)
        self.main_run()
        self.values_dict = None

    def select_method(self, method=1, day_coff=10, gap_coff=10, pr_coff=10):
        if not self.flag:
            self.day_coff = day_coff
            self.gap_coff = gap_coff
            self.pr_coff = pr_coff

    def main_run(self):
        self.dt = self.dt.apply(self.fill_score, axis=1)
        self.dt['درس'] = self.index_trim(self.dt['درس'])
        self.values_dict = self.values_dict_gen(self.dt)
        self.selector(self.values_dict)
        if not self.flag:
            sorted_list = self.evaluate_matrix()
            self.print_matrix(sorted_list)






    def fill_score(self, row):
        if pd.isna(row['امت?از']):
            dt_gp = self.dt.groupby(by='درس').agg({'امت?از': 'mean'})
            if not pd.isna(dt_gp['امت?از'][dt_gp.index == row['درس']].values[0]):
                row['امت?از'] = dt_gp['امت?از'][dt_gp.index == row['درس']].values[0]
            else:
                row['امت?از'] = 5
        return row


    @staticmethod
    def values_dict_gen(data):
        values_dict = defaultdict(list)
        for indx, row in data.iterrows():
            values_dict[row[0]].append((row[1], row[2], row[3]))
        return values_dict


    @staticmethod
    def standardize_persian_text(text, flag=True):
        if flag:
            return text[0].replace('ي', 'ی').replace('ك', 'ک').replace('?', 'ی')
        return text.replace('ي', 'ی').replace('ك', 'ک').replace('?', 'ی')


    def trim_query(self, query):
        query_split = query.split(' ')
        query_drop_space = [i for i in query_split if i]

        cleaned_data = []
        for i in range(len(query_drop_space)):
            if not (query_drop_space[i] == 'از' and i > 0 and query_drop_space[i - 1] == 'از'):
                cleaned_data.append(query_drop_space[i])

        return cleaned_data


    @staticmethod
    def convert_day_to_int(query):
        map_day = {
            'شنبه': 0,
            'یکشنبه': 1,
            'دوشنبه': 2,
            'سه': 3,
            'چهارشنبه': 4,
            'پنج': 5
        }
        query_edit = []
        for i in query:
            if i in map_day:
                query_edit.append(map_day[i])
            else:
                query_edit.append(i)
        if query_edit[1] == 0:
            del query_edit[1]
        if len(query_edit) > 6:
            if query_edit[6] == 0:
                del query_edit[6]
        return query_edit


    @staticmethod
    def convert_time_to_int(time_str):
        hour = time_str.split(':')[0]
        hour_int = int(hour)

        return hour_int


    def time_series(self, query):
        if len(query) > 8:
            index = [2, 4, 7, 9]
        else:
            index = [2, 4]
        sample = []

        for i in index:
            sample.append(self.convert_time_to_int(query[i]))

        return sample


    def check_class(self, query, hours):

        if len(query) > 8:
            day = [query[0], query[5]]
        else:
            day = [query[0]]
        for i in range(0, len(hours), 2):

            if hours[i + 1] - hours[i] == 2:
                q = (hours[i] - 8) / 2
                if self.base_table[day[0]][int(q)] + 1 == 1:
                    day.pop(0)
                    continue
                else:
                    return False
            else:
                q = (hours[i] - 8) / 2
                if hours[i] % 2 == 0:
                    if self.base_table[day[0]][int(q)] != 0.25 and self.base_table[day[0]][int(q)] + 0.25 <= 1:
                        day.pop(0)
                        continue
                    else:
                        return False
                else:
                    if self.base_table[day[0]][int(q)] != 0.75 and self.base_table[day[0]][int(q)] + 0.75 <= 1:
                        day.pop(0)
                        continue
                    else:
                        return False
        return True


    def trim_three_hours(self, start_time, day):
        if start_time % 2 == 0:
            return [day, 'از', self.convert_to_time_format(start_time), 'تا', self.convert_to_time_format(start_time + 2), day, 'از',
                    self.convert_to_time_format(start_time + 2), 'تا', self.convert_to_time_format(start_time + 4)]
        return [day, 'از', self.convert_to_time_format(start_time - 1), 'تا', self.convert_to_time_format(start_time), day, 'از',
                self.convert_to_time_format(start_time), 'تا', self.convert_to_time_format(start_time + 2)]


    @staticmethod
    def convert_to_time_format(hour):
        return str(hour) + ":00"


    def tick_base_table(self, query, hours):
        if len(query) > 8:
            day = [query[0], query[5]]
        else:
            day = [query[0]]

        if hours[1] - hours[0] == 3:
            query = self.trim_three_hours(hours[0], query[0])
        if self.check_class(query, hours):

            for i in range(0, len(hours), 2):
                if hours[i + 1] - hours[i] == 2:
                    q = (hours[i] - 8) / 2
                    self.base_table[day[0]][int(q)] += 1
                else:
                    q = (hours[i] - 8) / 2
                    if hours[i] % 2 == 0:
                        self.base_table[day[0]][int(q)] += 0.25
                    else:
                        self.base_table[day[0]][int(q)] += 0.75
                day.pop(0)
            return True
        else:
            return False


    def pipline(self, title):
        title = self.standardize_persian_text(title)
        title_edit = self.trim_query(title)
        title_edit = self.convert_day_to_int(title_edit)
        title_hour = self.time_series(title_edit)
        if self.tick_base_table(title_edit, title_hour):
            return True
        return False


    def selector(self, class_list, i=0, selected=None):

        if selected is None:
            selected = []

        index_class = list(class_list.keys())

        if i >= len(index_class):
            dt_temp = pd.DataFrame(self.base_table)


            selected = ((data[0], data[1][0], data[1][1], data[1][2])for data in selected)

            dt_temp_course = pd.DataFrame(selected, columns=['Course', 'Schedule', 'Score', 'Name_pro'])
            dt_temp['id'] = self.c + 1
            dt_temp_course['id'] = self.c + 1
            self.c += 1
            self.df_matrix = pd.concat([self.df_matrix, dt_temp])
            self.df_matrix_course = pd.concat([self.df_matrix_course, dt_temp_course])

            return

        for j in range(len(class_list[index_class[i]])):
            base_table_copy = copy.deepcopy(self.base_table)
            selected_copy = selected.copy()

            flag = self.pipline(class_list[index_class[i]][j])

            if flag:
                selected_copy.append((index_class[i], class_list[index_class[i]][j]))
                self.selector(class_list, i + 1, selected_copy)

            self.base_table = base_table_copy


    def index_trim(self, indx):
        index_edit = []
        for i in indx:
            index_edit.append(i.replace('?', 'ی'))
        return index_edit


    def fitness_function(self, matrx, mean_score_mtrx):
        val_base = [(0.25, 0.75), (0.75, 0.25)]
        fitness_scores_list = []
        for i in val_base:

            matrix_copy = copy.deepcopy(matrx)

            matrix_copy = self.edd_oven(matrix_copy, i[0], i[1])
            days_present = np.sum(np.any(matrix_copy > 0, axis=1))
            gaps = 0

            for row in range(matrix_copy.shape[0]):
                class_indices = np.nonzero(matrix_copy.loc[row])[0]
                if len(class_indices) > 1:
                    for k in range(len(class_indices) - 1):
                        gaps += (class_indices[k + 1] - class_indices[k] - 1)

            fitness = self.day_coff * days_present + self.gap_coff * gaps + self.pr_coff * mean_score_mtrx
            fitness_scores_list.append(fitness)


        fitness_score = np.array(fitness_scores_list).mean()
        return fitness_score

    @staticmethod
    def edd_oven(matrx, one_val, zero_val):
        matrx[matrx == one_val] = 1
        matrx[matrx == zero_val] = 0
        return matrx


    def evaluate_matrix(self):
        point_list = []
        id_table = 0
        for table in range(0, self.df_matrix.shape[0], 6):
            id_table += 1
            mean_score_local_matrix = self.df_matrix_course[self.df_matrix_course['id'] == id_table]['Score'].mean()

            point = self.fitness_function(self.df_matrix.iloc[table:table + 6, :6], mean_score_local_matrix)
            point_list.append((id_table, point))
        point_list.sort(key=lambda x: x[1])
        return np.array(point_list)

    def print_matrix(self, srt_list):
        programs = []
        for i, program_id in enumerate(srt_list[:, 0], start=1):
            messages = []
            messages.append('*/' * 25)
            messages.append(f"برنامه {i}: {program_id}")
            messages.append('*/' * 25)
            # حداقل جدول
            minimum_table = self.df_matrix[self.df_matrix['id'] == program_id].iloc[:, :6]
            minimum_table.index = ['SAT', 'SUN', 'MON', 'TUE', 'WED', 'THU']
            minimum_table.columns = ['"8-10', '"10-12', '"12-14', '"14-16', '"16-18', '"18-20']
            messages.append(minimum_table.to_string())
            # جزئیات دوره‌ها
            course = self.df_matrix_course[self.df_matrix_course['id'] == program_id][
                ['Course', 'Schedule', 'Score', 'Name_pro']]
            for detail in course.itertuples():

                messages.append(f"Course: {detail.Course}")
                messages.append(f"Time: {detail.Schedule}")
                messages.append(f"Score: {detail.Score}")
                messages.append(f"Name Pro: {self.standardize_persian_text(detail.Name_pro, flag=False)}")
                messages.append('-'*10)
            programs.append('\n'.join(messages))
        return programs

    def all_model(self, courses, id):
        filtered_rows = pd.DataFrame()

        for _, record in courses.iterrows():
            course = record['Course']
            name_pro = record['Name_pro']

            filtered_dt = self.dt[(self.dt['درس'] == course) & (self.dt['استاد'] == name_pro)]
            filtered_rows = pd.concat([filtered_rows, filtered_dt], ignore_index=True)

        new_unit_selection = UnitSelection(data=filtered_rows, flag=True, id=id)

        return new_unit_selection.df_matrix_course






end_time = time.time()
print(end_time-srt_time)
