$(function() 
{
    /**
     * Init global variables
     */
    let sessionId = null
    let timer = null
    let timeout = 0
    let rpmMax = 0
    let rpmAvg = 0
    let acceleration = 0
    let accelerationMax = 0
    let angularVelocity = 0
    let peripherySpeed = 0
    let distanceTravelled = 0
    let materialWeight = 0
    let diskSurfaceAreaGross = 0
    let diskSurfaceAreaNet = 0
    let diskVolume = 0
    let diskMass = 0
    let totalRotorMass = 0
    let diskCircumference = 0
    let rpmForSupersonic = 0
    const speedOfSound = 343.2  // meters per second
    const diskMinusPortsPercentage = 0.55  // A rough estimate based on Tesla's patent drawings that ~ half of the disk is ports, spokes, or shaft


    /**
     * Open / close settings
     */
    $( "#settings-btn" ).on( "click", function() {
        $( ".sheet-overlay" ).addClass( "sheet-overlay-active" )
        $( ".sheet" ).addClass( "sheet-active" )
    })

    $( ".sheet-overlay, #settings-close-btn" ).on( "click", function() {
        $( ".sheet-overlay" ).removeClass( "sheet-overlay-active" )
        $( ".sheet" ).removeClass( "sheet-active" )
    })


    /**
     * Handle settings form changes
     * @param {string} units The units to set the values to (metric || imperial)
     */ 
    function setUnits(units)
    {
        if (units === "metric") {
            $("#settings-form .unit").text("mm")
            $("#settings-form #disk-diameter").prop("step", "1")
            $("#settings-form #disk-thickness").prop("step", "0.1")
        } else if (units === "imperial") {
            $("#settings-form .unit").text("in")
            $("#settings-form #disk-diameter").prop("step", "0.1")
            $("#settings-form #disk-thickness").prop("step", "0.01")
        }
    }

    function applySettings()
    {
        const diskDiameter = $("#disk-diameter").val()
        const diskRadius = diskDiameter / 2
        const diskThickness = $("#disk-thickness").val()
        const diskCount = $("#disk-count").val()

        // Set variables
        materialWeight = $("#disk-material").val()
        diskSurfaceAreaGross = Math.PI * diskRadius ** 2
        diskSurfaceAreaNet = diskSurfaceAreaGross * diskMinusPortsPercentage
        diskVolume = (diskSurfaceAreaNet * diskThickness) / 1000
        diskMass = materialWeight * diskVolume
        totalRotorMass = diskMass * diskCount
        diskCircumference = Math.PI * diskDiameter
        rpmForSupersonic = (speedOfSound / diskCircumference) * 60000

        // Display values
        $("#materialWeight").text(materialWeight)
        $("#diskSurfaceAreaGross").text( Math.round(diskSurfaceAreaGross * 100) / 100 )
        $("#diskSurfaceAreaNet").text( Math.round(diskSurfaceAreaNet * 100) / 100 )
        $("#diskVolume").text( Math.round(diskVolume * 100) / 100 )
        $("#diskMass").text( Math.round(diskMass * 100) / 100 )
        $("#totalRotorMass").text( Math.round(totalRotorMass * 100) / 100 )
        $("#diskCircumference").text( Math.round(diskCircumference * 100) / 100 )
        $("#rpmForSupersonic").text( Math.round(rpmForSupersonic) )
    }

    function saveSettings()
    {
        var  formData = []

        // Remove old formData
        localStorage.removeItem('settings')

        // Loop through form input fields
        $("#settings-form input[type=number], #settings-form select, #settings-form input[type=radio]:checked").each(function() {
            formData.push({ 
                name: this.name, 
                value: $(this).attr('type') === "radio" ? this.id : this.value,
                type: $(this).attr('type')
            })
        })

        // Convert array to JSON and story in localStorage
        localStorage.settings = JSON.stringify(formData)
    }

    function loadSettings()
    {
        if (localStorage.settings != undefined) {
            settings  = JSON.parse(localStorage.settings)
            for (var i = 0; i < settings.length; i++) {
                if (settings[i].type != undefined && settings[i].type == "radio")
                {
                    $("#" + settings[i].value).prop('checked', true)
                } else {
                    $("[name=" + settings[i].name + "]").val(settings[i].value)
                }

                if (settings[i].name === "units")
                {
                    setUnits(settings[i].value)
                }
            }
        } else {
            setUnits("metric")
        }

        applySettings()
    }
    
    // Get form data from localstorage on page load
    loadSettings()

    // Listen for changes in the settings form
    $("#settings-form input, #settings-form select").on( "input", function() 
    {
        applySettings()

        // Don't save settings on every change immediately, but wait a little to batch them
        clearTimeout(timeout);

        timeout = setTimeout(function() {
            saveSettings()
        }, 3000)
    })

    $("#settings-form input[name=units]").on( "change", function() {
        setUnits(this.id)
    })


    /**
     * Create charts
     */
    rpmChart = new Chart('rpm-chart', {
        type: 'line',
        options: {
            scales: {
                y: {
                    ticks: {
                        color: '#95aac9',
                        callback: function(value) {
                            return (value / 1000) + 'k';  // Thousands of RPM 
                        }
                    },
                    grid: {
                        display: true,
                        color: "rgba(227,235,246,.1)",
                        borderDash: [2, 2]
                    }
                    //beginAtZero: true
                },
                x: {
                    //type: 'timeseries',
                    ticks: {
                        color: '#95aac9',
                        autoSkip: true,
                        maxTicksLimit: 20
                    },
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false,  // We're going to need to display a legend when we show 2 readings in one chart
                }
            }
        },
        data: {
            labels: [],
            datasets: [{
                label: 'RPM1',
                data: [],
                tension: 0.5,
                borderColor: '#2c7be5'
            }]
        }
    });


    /**
     * Reset all data in the dashboard to its initial state
     */
    function reset() 
    {
        // Reset all charts
        ticks = 0
        rpmChart.data.labels = []
        rpmChart.data.datasets.forEach((dataset) => {
            dataset.data = []  // Set to empty array
        })
        rpmChart.update()

        // Reset calculations like averages
        rpmMax = 0
        rpmAvg = 0
    }


    /**
     * Display sensor data on dashboard
     * 
     * @param {object} data JSON object containing one reading of all sensors
     */
    function displayData(data)
    {
        displayRpm(data)
        
        $("#card-temp .card-text").html(data.temperature + "&deg;")  // @TODO: convert to Fahrenheit if Imperial is selected

        $("#session-id").text(data.sessionId === null ? 'No active session' : data.sessionId)

        // How to handle averages? Can't loop through all items every 500ms
        // Should probably add up a total, and then read the length of the array so we know what to divide with

        if (sessionId === null && data.sessionId !== null)
        {
            // New session, so reset all charts and calculations
            reset()
            timer = startTimer()
        } else if (sessionId === null && data.sessionId === null)
        {
            // No session, don't update averages and other calculations, only live values
        } else if (sessionId !== null && data.sessionId === null)
        {
            // End session
            stopTimer(timer)
            timer = null
        } else {
            // Active session
        }
    }


    /**
     * Find the average of all numbers in an array 
     * 
     * @param {array} array Take the average of an array of data
     * @returns The average
     */
    function average(array) {
        return array.reduce((a, b) => (a + b)) / array.length;
    }


    /**
     * Display RPM, update RPM chart, and calculate related values
     * 
     * @param {object} data JSON object containing one reading of all sensors 
     */
    function displayRpm(data)
    {
        // Display RPM
        $('#card-rpm .card-text').text(data.rpm.toString().split(/(?=.{3}$)/).join(' ') + ' RPM')  // Add space to separate thousands

        // Update RPM chart
        const dataPoints = rpmChart.data.datasets[0].data.length + 1
        let label = dataPoints * loopIntervalMs / 1000  // The x-axis label is the number of seconds since start of session, determined by number of data points * loop interval
        rpmChart.data.labels.push(label)
        rpmChart.data.datasets[0].data.push(data.rpm)
        rpmChart.update()

        // Calculations
        rpmMax = Math.max(rpmMax, data.rpm)
        rpmAvg = average(rpmChart.data.datasets[0].data)
        let accelerationOld = acceleration
        acceleration = 0
        accelerationMax = Math.max(accelerationOld, acceleration)
        angularVelocity = 0
        peripherySpeed = 0
        distanceTravelled = 0


        // Display the results of the calculations
        $("#rpmMax").text( Math.round(rpmMax) )
        $("#rpmAvg").text( Math.round(rpmAvg) )
    }


    /**
     * Start a timer to count the duration of a session
     * 
     * @returns {object} The timer object 
     */
    function startTimer()
    {
        let seconds = 0
        function pad ( val ) { return val > 9 ? val : "0" + val; }
        return setInterval( function() {
            $("#seconds").html(pad(++seconds%60))
            $("#minutes").html(pad(parseInt(seconds/60,10)))
        }, 1000)
    }


    /**
     * Stop a timer
     * 
     * @param {object} timer The timer object
     */
    function stopTimer(timer)
    {
        clearInterval ( timer )
    }


    $("#valve-btn").on( "click", function() 
    {
        let currentState = $(this).data( "state" )
        let newState = !currentState

        openValve(newState)
    })


    /**
     * Open or close an electronic valve to start or stop a test session
     * 
     * @param {boolean} state True to open valve, false to close valve
     */
    function openValve(state)
    {
        // Show loading indicator
        $("#valve-btn .fe").removeClass("fe-play-circle").addClass("fe-clock")

        let request_data = {
            action: state === true ? "open_valve" : "close_valve"
        }

        $.ajax({
            type: "POST",
            url: "server.py",
            contentType: "json",
            dataType: "json",
            data: JSON.stringify(request_data),
            success: function(data, text)
            {
                console.log(data)

                // Update button state in Dashboard
                if (data.valveOpen === true)
                {
                    // Set button to opened state (show stop)
                    $("#valve-btn").data( "state", true )
                    $("#valve-btn .fe").removeClass("fe-clock").addClass("fe-stop-circle")
                } else {
                    // Set button to closed state (show play)
                    $("#valve-btn").data( "state", false )
                    $("#valve-btn .fe").removeClass("fe-stop-circle").addClass("fe-play-circle")
                }
            }, 
            error: function (request, status, error) {
                console.error(request.responseText)
                $("#valve-btn .fe").removeClass("fe-clock").removeClass("fe-stop-circle").addClass("fe-play-circle")
                $("#valve-btn").data( "state", false )
            },
        })
    }


    let loopIntervalMs = 5000  // How often we request data from the sensors

    /**
     * This loop polls the Python sensor reading script every 500ms for new data
     */
    function loop() 
    {
        let request_data = {
            action: "read_sensors"
        }

        $.ajax({
            type: "POST",
            url: "server.py",
            contentType: "json",
            dataType: "json",
            data: JSON.stringify(request_data),
            success: function(data, text)
            {
                console.log(data)

                // Update data in Dashboard
                displayData(data)

                sessionId = data.sessionId
            }, 
            error: function (request, status, error) {
                console.error(request.responseText)
            },
        })

        setTimeout(loop, loopIntervalMs)
    }

    loop()
})