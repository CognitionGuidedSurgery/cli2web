import cli2web

__author__ = 'weigl'

if __name__ == "__main__":
    app = cli2web.setup(["/homes/students/weigl/workspace1/mup-nifty/build/reg-apps/reg_aladin"])
    app.run(host="0.0.0.0", debug=True)