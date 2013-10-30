module.exports = function(grunt) {

  // load all grunt tasks
  require('matchdep').filterDev('grunt-*').forEach(grunt.loadNpmTasks);

  grunt.initConfig({

    compass: {
      dev: {
        options: {
          config: 'media/sass/config.rb',
          basePath: 'media/sass',
          // outputStyle: 'compressed',
          force: true
        }
      }
    },

    exec: {
      update: {
        cmd: 'bower update'
      },
      runserver: {
        cmd: 'cd readthedocs && ./manage.py runserver'
      }
    },

    watch: {
      sass: {
        files: ['media/**/*.sass', 'media/bower_compoents/**/*.sass'],
        tasks: ['compass:dev']
      },
      /* watch our files for change, reload */
      livereload: {
        files: ['**/*.html', '**/*.css', '**/*.js'],
        options: {
          livereload: true
        }
      },
    }

  });

  grunt.loadNpmTasks('grunt-exec');
  grunt.loadNpmTasks('grunt-contrib-compass');

  grunt.registerTask('default', ['exec:update', 'watch']);
  grunt.registerTask('serve', ['exec:runserver']);

}



