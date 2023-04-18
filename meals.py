# TO DO:
# When a dish is deleted, set the field of any meal that refers to that dish to null

# for why the program returns error code 422 when the ID of a course in a meal is not found see:
# https://stackoverflow.com/questions/42143115/which-status-code-is-correct-404-or-400-and-when-to-use-either-of-these
#
# This is example REST API server code for assignment #1
# It uses Flask to build a REST service in Python.
# a good introduction is https://towardsdatascience.com/the-right-way-to-build-an-api-with-python-cd08ab285f8f
# see also https://dzone.com/articles/creating-rest-services-with-flask
#
# To run on cmd line, set env variables and then run flask:
# export FLASK_APP=meals.py
# export FLASK_RUN_PORT=80
# export FLASK_RUN_HOST=0.0.0.0
# flask run --port 80   or:  flask run

# The resources are:
# /dishes             These are a collection of dishes.  Each dish has a unique name and is given a unique key.
# /dishes/{ID} and /dishes/{Name}
# This refers to a specific dish.  It can be identified either by /dishes/{ID} or /dishes/{name}
# each dish is a JSON structure: {"name": name,"ID": ID, "cal": cal, "size": size,"sodium": sodium, "sugar": sugar}
# /meals              This refers to the collection of meals.  Each meal has a unique key
# /meals/{ID} and /meals/{name}
# This refers to a specific meal.  It can be identified either by /meals/{ID} or /dishes/{name}
# each meal is a JSON structure: {"name": name, "ID": ID, "appetizer": ID, "main": ID, "dessert": ID,"cal": cal,
#                                 "sodium": sodium, "sugar": sugar}}

# we use the Flask request package when working with Flask APIs that we create
# however, when invoking API-Ninja APIs, just use python requests package.
from flask import Flask, request   # , jsonify
from flask_restful import Resource, Api
import requests
import sys
from meal_exceptions import DishNotDefined, APINotReachable, SomeAPIError  # customized exception names
import os.path
if os.path.isfile("My_Ninja_key.py"):
    from My_Ninja_key import NINJA_API_KEY
else:
    from Ninja_key import NINJA_API_KEY

app = Flask(__name__)  # initialize Flask
api = Api(app)  # create API

global courses
# I have changed the status codes to be returned.   Specifically, (1) if there is an error is the request message,
# then status code 422 should be returned in place of 400, (2) if an API is called and it does not respond, then
# status code 504 should be returned in place of 400, and (3) some other changes -- see code below
# Since I had already told one class they could return 400, I will stick with that if A==True.  Otherwise return the
# updated status code.
global A

# Dishes, Dish, Meals and Meal are resources visible to external users.   Internally, we use data structures for these
# entities.   To avoid confusion between the resource classes (that flask will route requests to) and internal classes,
# we use Courses, Course, Menus, and Menu for the internal equivalents of Dishes, Dish, Meals and Meal.
# findCourseInfo takes the name of a course (dish) and uses the nutrition API from NINJA APIs to retrieve the calories,
# serving size (in grams), sodium (in mg) and sugar (in grams) of the course.  If the API does not return a valid
# result, then it will throw an error and set all the fields to 0.
def findCourseInfo(name):
    query = name
    api_url = 'https://api.api-ninjas.com/v1/nutrition?query={}'.format(query)
    try:
        response = requests.get(api_url, headers={'X-Api-Key': NINJA_API_KEY})
    except:
        print("Error from api.api-ninjas.com/v1/nutrition.  response code = ", response.status_code)
        print("response text = ", response.text)
        print("raising SomeAPIError")
        sys.stdout.flush()
        raise SomeAPIError
    else:
        if response.status_code == requests.codes.ok:
            try:
                # the response might include multiple items.  E.g., if the query to Ninja is for "cereal and eggs", it
                # will return one item for cereal and one for eggs.  However, "cereal and eggs" is treated as one dish,
                # so the calories, sodium, etc. of the dish is the sum of the calories, sodium, etc. of the items in the
                # response.
                resp = response.json()
                if not resp:  # response.json() is empty
                    raise Exception
                calories = 0
                serving_size = 0
                sodium = 0
                sugar = 0
                for val in resp:
                    calories += val.get("calories")
                    serving_size += val.get("serving_size_g")
                    sodium += val.get("sodium_mg")
                    sugar += val.get("sugar_g")
                return calories, serving_size, sodium, sugar
            except:  # if API returns empty text, then this dish is not found.   Raise DishNotDefined exception
                print("Response Error from api.api-ninjas.com/v1/nutrition.  response code = ", response.status_code)
                print("response text = ", response.text)
                # print("if empty text then API did not recognize dish called ", name)
                print("raising DishNotDefined")
                sys.stdout.flush()
                raise DishNotDefined
        else:  # bad response code from api.api-ninjas.com/v1/nutrition.   Probably "502" Internal Server error.  Need
               # to retry
            print("Bad response code from api.api-ninjas.com/v1/nutrition.  response code = ", response.status_code)
            print("response text = ", response.text)
            print("raising APINotReachable")
            sys.stdout.flush()
            raise APINotReachable  # need to add custom exception class to handle the different exceptions


# takes the name of a course and returns a JSON document for that course including calories and serving size
# the ID supplied becomes the ID field of the course
def makeCourse(name, ID):
    try:
        cal, size, sodium, sugar = findCourseInfo(name)
    except APINotReachable:  # server not responding
        raise APINotReachable  # propagate exception
    except DishNotDefined:  # API does not recognize this dish name
        raise DishNotDefined  # propogate error
    except SomeAPIError:  # some other API error
        raise SomeAPIError  # propagate exception
    else:  # findCourseInfo was successful
        course = {
            "name": name,
            "ID": ID,
            "cal": cal,
            "size": size,
            "sodium": sodium,
            "sugar": sugar
        }
        return course


# Courses is an internal class used to store information about courses.   A course is the same as a dish.
class Courses:
    def __init__(self):
        self.courseID = 0
        self.courses = {}

    # addCourse returns the courseID for the new dish added, if operation is successful.  Otherwise it returns:
    # -2 if the dish of supplied name already exists.
    # -3 if api.api-ninjas.com/v1/nutrition does not recognize this dish name.
    # -4 if api.api-ninjas.com/v1/nutrition was not reachable or some other server error. E
    def addCourse(self, name):
        self.courseID = self.courseID + 1
        try:
            if name in [n['name'] for n in self.courses.values()]:
                print(("Course name  " + name + " already defined"))
                sys.stdout.flush()
                return -2  # courseID == -2 means that dish of given name already exists
            else:
                self.courses[self.courseID] = makeCourse(name, self.courseID)
        except DishNotDefined:
            # return -3 means that api.api-ninjas.com/v1/nutrition does not recognize this dish name
            return -3
        except APINotReachable:
            # return -4 means that api.api-ninjas.com/v1/nutrition was not reachable
            return -4
        except SomeAPIError:
        # return -4 means also if api.api-ninjas.com/v1/nutrition returned another error condition
            return -4
        else:
            return self.courseID

    # deleteCourse returns True if courseID was valid and therefore deletion was successful, otherwise returns False
    def deleteCourse(self, courseID):
        try:
            del self.courses[courseID]
            return True  # Course was deleted successfully
        except KeyError:
            return False  # False means that this courseID is not valid

    # If the dish ID supplied is valid, findCourse returns the course corresponding to the dish ID.
    # Otherwise it returns None
    def findCourse(self, courseID):
        try:
            return self.courses[courseID]
        except KeyError:
            return None  # None for course means that this courseID is not valid

    # If the dish_name supplied is valid, findCourse returns the course corresponding to that dish.
    # Otherwise it returns None
    def findCourseIDbyName(self, dish_name):
        courseID = None
        for key, value in self.courses.items():
            if dish_name == value['name']:
                courseID = key
                break
        return courseID

    # listCourses returns the dictionary mapping dish IDs to dishes
    def listCourses(self):
        return self.courses

    # insertCourse adds the given course to the collection of courses and returns that course's ID
    def insertCourse(self, course):
        self.courseID = self.courseID + 1
        self.courses[self.courseID] = course
        return self.courseID


# Dishes implements the /dishes resource.  It uses courses (an instance of the Courses class) to store/retrieve
# information on dishes.
class Dishes(Resource):
    # courses is an instance of the Courses class, initialized by the main program on startup
    global courses

    # POST adds a dish to the Dishes resource and returns its ID with code 201 (success, resource created)
    # POST might fail because and will return non-positive IDs as follows:
    # ID == 0 means that content-type is not application/json.  Error code 415 (Unsupported Media Type)
    # ID == -1 means that 'name' parameter was not specified.  Error code 400 (Bad request)
    # ID == -2 means that dish of given name already exists. Error code 400
    # ID == -3 means that api.api-ninjas.com/v1/nutrition does not recognize this dish name. Error code 400
    # ID == -4 means that api.api-ninjas.com/v1/nutrition was not reachable or some other server error. Error code 400
    def post(self):
        content_type = request.headers.get('Content-Type')
        if content_type == 'application/json':
            try:
                courseName = request.json['name']
            except KeyError:  # no such parameter "name"
                print("POST /dishes exception: 'name' parameter not supplied")
                sys.stdout.flush()
                if A:
                    return -1, 400  # 400 Bad Request.   0 returned key value means that for  was not successful
                else:
                    return -1, 422
            else:  # found parameter
                key = courses.addCourse(courseName)
                if key > 0:  # successful course creation
                    return key, 201
                else:  # operation not successful.  key is negative and gives error code
                    if key == -4:  #API Ninjas nutrition API error (timeout,...)
                        if A:
                            return key, 400
                        else:
                            return key, 504
                    # otherwise error in request message content so return 422
                    if A:
                        return key, 400
                    else:
                        return key, 422
                # except NameError:
                #     print("courses not initialized")
                #     sys.stdout.flush()
                # except:  #API Ninjas nutrition API was unreachables
                #     if A:
                #         return -4, 400  # for any other exceptions return courseID of -4
                #     else:
                #         return -4, 504
        else:
            return 0, 415  # 415 Unsupported Media Type

    # returns the dictionary of all the courses in the dishes resource.
    def get(self):
        return courses.listCourses()


# Dish implements the /dishes/{dish} resource.  It uses courses (an instance of the Courses class) to store/retrieve
# information on each dish.
class Dish(Resource):
    # courses is an instance of the Courses class, initialized by the main program on startup
    global courses

    # GET takes either a dish ID or a dish name and returns the JSON object containing for that dish with resp code 200.
    # (1) If neither the dish ID nor a dish name is specified, it returns -1 with error code 400 (Bad request).
    # (2) if dish name or dish ID does not exist, it returns -5 with error code 404 (Not Found).
    def get(self, ID=None, name=None):
        # ID, if present, is ID (integer) of dish. name, if present, is the name (string of dish)
        # One of these must be present otherwise the request would be GET /dishes
        if ID:  # ID is supplied
            dishID = int(ID)  # convert ID to integer
        else:  # then name is supplied
            name = name.strip()  # remove any leading or trailing whitespaces
            dishID = courses.findCourseIDbyName(name)
            if dishID is None:  # no such course given by name
                return -5, 404
        #   # if reach here then dishID is an integer, the dish (course) ID
        try:
            dish = courses.findCourse(dishID)
            return dish, 200
        except:  # dish ID provided in not valid
            return -5, 404

    # DELETE takes either a dish ID or a dish name and deletes that dish.  It returns the ID of the deleted dish with
    # response code 200 (success)
    # (1) If neither the dish ID nor a dish name is specified, it returns -1 with error code 400 (Bad request)
    # (2) If dish name or dish ID does not exist, it returns -5 with error code 404 (Not Found)
    def delete(self, ID=None, name=None):
        # ID, if present, is ID (integer) of dish. name, if present, is the name (string of dish)
        # cannot have ID and name missing because then request would be DELETE /dishes and the return code would be
        # generated by Flask with return code 405 (Method not allowed)
        if ID:
            dishID = int(ID)  # convert ID to integer
        else:  # then name is supplied
            name = name.strip()  # remove any leading or trailing whitespaces
            dishID = courses.findCourseIDbyName(name)
            if dishID is None:  # no such course given by name
                return -5, 404
        # if reach here then dishID is an integer, the dish (course) ID
        success = courses.deleteCourse(dishID)
        if success:
            return dishID, 200
        else:  # dish ID provided in not valid
            return -5, 404


# takes the name of a menu item and IDs for the appetizer, main, and dessert courses.  It returns a JSON document for
# that menu item including the total calories of the menu item
def makeMenu(name, ID, appetizerID, mainID, dessertID):
    global courses
    try:
        appetizer = courses.findCourse(appetizerID)
        main = courses.findCourse(mainID)
        dessert = courses.findCourse(dessertID)
        cal = appetizer["cal"] + main["cal"] + dessert["cal"]
        sodium = appetizer["sodium"] + main["sodium"] + dessert["sodium"]
        sugar = appetizer["sugar"] + main["sugar"] + dessert["sugar"]
        menu = {
            "name": name,
            "ID": ID,
            "appetizer": appetizerID,
            "main": mainID,
            "dessert": dessertID,
            "cal": cal,
            "sodium": sodium,
            "sugar": sugar
        }
        return menu
    except:
        print("makeMenu: KeyError")
        sys.stdout.flush()
        return None


# Menus is an internal class used to store information about menus.   A menu is the same as a meal.
class Menus:
    def __init__(self):
        self.menuID = 0
        self.menus = {}

    # addMenu will add a completely new menu for POST request.  In this case, menu_ID is not passed in.
    # addMenu will also be used for PUT request, in which case the existing menu_ID is passed in (it is reused).
    def addMenu(self, menu_name, appetizerID, mainID, desertID, menu_ID = None):
        if menu_ID is None:
            # then trying to add new meal with name menu_name.   Need to check that this name does not already exist
            if self.findMenuIDbyName(menu_name) !=  None:
                # -2 return value means that the menu_name already exists
                return -2
            else:
                # menu_name is a new meal name.   assign a new ID
                self.menuID = self.menuID + 1
                menu_ID = self.menuID
        else:
            # trying to update menu with existing ID menu_ID
            if menu_ID not in self.menus.keys():     # if menu_ID passed in is not a valid meal ID
                return -5  # -5 return value means that menu_ID is not a valid ID
                # ******  NEED to check that menu_name being supplied for existing meal, if different from existing
                # menu_name, does not already exist as the name of another menu.
                # ******  MAYBE say that can supply only a menu_ID or a menu_NAME but not both????
        # if we reach here, menu_ID is the ID for a new or existing meal
        menu = makeMenu(menu_name, menu_ID, appetizerID, mainID, desertID)
        if menu is None:
            print("addMenu:  menu == None")
            # returned menu is None then one of the dish IDs does not exist.  the menu was not added.
            if A:
                print("returning -5")
                return -5  # -5 is overloaded & covers two different cases that should have different status codes
            else:
                print("returning -6")
                return -6  # -6 means that one of the sent dish IDs (appetizer, main, dessert) does not exist.
        else:
            self.menus[menu_ID] = menu
            return menu_ID

    def findMenu(self, menuID):
        try:
            return self.menus[menuID]
        except KeyError:
            raise KeyError

    def findMenuIDbyName(self, menu_name):
        menuID = None
        for key, value in self.menus.items():
            if menu_name == value['name']:
                menuID = key
                break
        return menuID

    def deleteMenu(self, menuID):
        try:
            del self.menus[menuID]
            return True  # meal was deleted successfully
        except KeyError:
            return False  # False means that this mealID is not valid

    def updateMenuName(self, ID, new_name):
        try:
            menu = self.menus[ID]
            menu['name'] = new_name
            self.menus[ID] = menu
            return True
        except:
            return False

    def listMenus(self):
        return self.menus


# Menus implements the /meals resource.  It uses menus (an instance of the Menus class) to store/retrieve
# information on dishes.
class Meals(Resource):
    global menus

    # post adds a meal to Menus and returns its key
    def post(self):
        content_type = request.headers.get('Content-Type')
        if content_type == 'application/json':
            try:
                mealName = request.json['name']
                appetizerID = int(request.json['appetizer'])
                mainID = int(request.json['main'])
                desertID = int(request.json['dessert'])
            except:
                # one of the required parameters was not supplied
                if A:
                    return -1, 400
                else:
                    return -1, 422
            else:
                menuID = menus.addMenu(mealName, appetizerID, mainID, desertID)
                print("post: menuID = ", menuID)
                if menuID > 0:
                    # a positive menuID indicates that the mean was added with the new ID menuID
                    return menuID, 201
                else:
                    # could not create this menu
                    if (menuID == -5):   # for A it is -5 (overloaded), for (not A) it is -6
                        # then one of the dish IDs supplied were not found
                        return -5, 404  # 404 Not Found
                    elif (menuID == -6):
                        return -6, 422
                    elif menuID == -2:
                        # the mealName already exists
                        if A:
                            return -2, 400
                        else:
                            return -2, 422
                    else:
                        # currently, no other negative values can be returned from addMenu but for future extensions this is here
                        return menuID, 400
        else:
            print("content_type is not application/json.   content_type = ", str(content_type))
            sys.stdout.flush()
            return 0, 415  # 415 Unsupported Media Type

    # returns all the meals in the collection.
    def get(self):
        return menus.listMenus()  # returns dictionary of menus (meals)


class Meal(Resource):
    def get(self, ID=None, name=None):   # ID, if present, is int. name, if present, is str.
        # ID, if present, is ID (integer) of the meal.  name, if present, is the name (string) of the meal.
        # We cannot have ID and name missing because then request would be GET /meals and this method would not be
        # executed
        if ID:  # ID is supplied.  it is a string so need to convert it to int
            mealID = int(ID)
        else:  # then name is supplied
            name = name.strip()  # remove any leading or trailing whitespaces
            mealID = menus.findMenuIDbyName(name)
            if mealID is None:  # no such course given by name
                return -5, 404
        # if reach here then mealID is an integer, the meal ID
        try:
            meal = menus.findMenu(mealID)
            return meal, 200
        except:  # meal ID provided in not valid
            return -5, 404

    def delete(self, ID=None, name=None):   # ID, if present, is integer. name, if present, is string.
        # ID, if present, is ID (integer) of the meal.  name, if present, is the name (string) of the meal.
        # We cannot have ID and name missing because then request would be DELETE /meals and the return code would be
        # generated by Flask with return code 405 (Method not allowed)
        if ID:  # ID is supplied.  it is a string so need to convert it to integer
            mealID = int(ID)
        else:  # then name is supplied
            name = name.strip()  # remove any leading or trailing whitespaces
            mealID = menus.findMenuIDbyName(name)
            if mealID is None:  # no such course given by name
                return -5, 404
        # if reach here then mealID is an integer, the meal ID
        if menus.deleteMenu(mealID):
            return mealID, 200
        else:  # meal ID provided in not valid
            return -5, 404

    # PUT acts exactly like POST except the meal ID aleady exists.   The meal name, appetizer, main and dessert dish ID
    # must be supplied in a JSON object.
    def put(self,ID):  # ID is ID of meal to update name
        content_type = request.headers.get('Content-Type')
        if content_type == 'application/json':
            try:
                mealName = request.json['name']
                appetizerID = int(request.json['appetizer'])
                mainID = int(request.json['main'])
                desertID = int(request.json['dessert'])
            except:
                # one of the required parameters was not supplied
                if A:
                    return -1, 400
                else:
                    return -1, 422
            else:
                menuID = menus.addMenu(mealName, appetizerID, mainID, desertID, ID)
                if menuID > 0:
                    return menuID, 200
                else:
                    # could not create this menu - one of the dish IDs or the meal ID supplied was not found
                    if A:
                        return menuID, 404
                    else:
                        if menuID == -5:
                            return menuID, 404  # the ID passed in is Not Found
                        else:
                            return menuID, 422  # either missing parameter or incorrect parameter
        else:
            print("content_type is not application/json.   content_type = ", str(content_type))
            sys.stdout.flush()
            return 0, 415  # 415 Unsupported Media Type

@app.before_first_request
# This code gets executed when application is started by Flask.   Initializes global data structures needed.
def before_first_request_func():
    global courses
    global menus
    global A
    courses = Courses()
    print("created courses")
    sys.stdout.flush()
    menus = Menus()
    A = True


# associate the Resource '/dishes' with the class Dishes
# associate the Resource '/meals' with the class Meals
# associate the Resource '/words/total' with the class Count
api.add_resource(Dishes, '/dishes')
api.add_resource(Dish, '/dishes/<int:ID>', endpoint='/dishes/<int:ID>')
api.add_resource(Dish, '/dishes/<string:name>', endpoint='/dishes/<string:name>')
api.add_resource(Meals, '/meals')
api.add_resource(Meal, '/meals/<int:ID>', endpoint='/meals/<int:ID>')
api.add_resource(Meal, '/meals/<string:name>', endpoint='/meals/<string:name>')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # initialize courses and menus dictionaries
    courses = Courses()
    print("created courses")
    sys.stdout.flush()
    menus = Menus()
    # # enter some test data
    # co = {'name': 'test1', 'ID': 1, 'cal': 204.3, 'size': 100.0, 'sodium': 430, 'sugar': 1.5}
    # courses.insertCourse(co)
    # co = {'name': 'test2', 'ID': 2, 'cal': 381.1, 'size': 100.0, 'sodium': 729, 'sugar': 1.9}
    # courses.insertCourse(co)
    # co = {'name': 'test3', 'ID': 3, 'cal': 32.3, 'size': 100.0, 'sodium': 256, 'sugar': 0.8}
    # courses.insertCourse(co)
    # co = {'name': 'test4', 'ID': 4, 'cal': 700.0, 'size': 100.0, 'sodium': 500, 'sugar': 2.8}
    # courses.insertCourse(co)
    # co = {'name': 'test5', 'ID': 5, 'cal': 300.4, 'size': 100.0, 'sodium': 550, 'sugar': 1.5}
    # courses.insertCourse(co)
    # co = {'name': 'test6', 'ID': 6, 'cal': 99.7, 'size': 100.0, 'sodium': 400, 'sugar': 1.3}
    # courses.insertCourse(co)
    # menus.addMenu("meal1", 1, 2, 3)
    # menus.addMenu("meal2", 4, 5, 6)
    # menus.addMenu("meal3", 4, 2, 6)
    # run Flask app.   the following command is only if running the program standalone.   We are running in a docker
    # container and use the Dockerfile + cmd line to run the program.
    # app.run(host='0.0.0.0', port=80, debug=True)

