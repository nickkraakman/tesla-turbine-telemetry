$(function() 
{
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
    }
    
    // Get form data from localstorage on page load
    loadSettings()

    // Listen for changes in the settings form
    let timeout = 0;

    $("#settings-form input, #settings-form select").on( "input", function() {
        // Don't save settings on every change immediately, but wait a little to batch them
        clearTimeout(timeout);

        timeout = setTimeout(function() {
            saveSettings()
        }, 3000)
    });

    $("#settings-form input[name=units]").on( "change", function() {
        setUnits(this.id)
    })


    /**
     * Create charts
     */
    new Chart('rpm-chart', {
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
                    ticks: {
                        color: '#95aac9',
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
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            datasets: [{
                label: 'Earned',
                data: [0, 1000, 5000, 15000, 10000, 20000, 15000, 25000, 20000, 30000, 25000, 40000],
                tension: 0.5,
                borderColor: '#2c7be5'
            }]
        }
    });


    /**
     * Display sensor data on dashboard
     * 
     * @param {object} data JSON object containing one reading of all sensors
     */
    function displayData(data)
    {
        // How to handle averages? Can't loop through all items every 500ms
        // Should probably add up a total, and then read the length of the array so we know what to divide with
    }


    /**
     * Call server to store the entire session as CSV on the SD card
     * 
     * @param {object} telemetrySession Object containing an array of sensor readings, session start, and session end time
     */
    function logSession(telemetrySession)
    {
        let request_data = {
            action: "log_session",
            payload: telemetrySession
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
            }, 
            error: function (request, status, error) {
                console.error(request.responseText)
            },
        })
    }


    let previousRpm = null

    /**
     * Store data temporarily in localStorage, and finally as CSV on SD card
     * 
     * @param {object} data JSON object containing one reading of all sensors
     */
    function storeData(data)
    {
        const currentRpm = "rpm" in data ? data.rpm : null

        // Check if we have to start a new session
        if (previousRpm === 0 && currentRpm > 0)
        {
            // Start new session
            telemetrySession = { 
                telemetry: [], 
                sessionStart: Date.now(),
                sessionEnd: null
            }

            // start session counter
        } else {
            if (localStorage.telemetrySession != undefined)
            {
                JSON.parse(localStorage.telemetrySession)
            } else {
                console.error("No telemetrySession found in localStorage")
            }
        }

        // Append new data
        telemetrySession.telemetry.push(data)

        // Check if we have to end this session
        if (previousRpm > 0 && currentRpm === 0)
        {
            telemetrySession.sessionEnd = Date.now()

            logSession(telemetrySession)

            localStorage.removeItem("telemetrySession")
        } else {
            // Store in localStorage
            localStorage.telemetrySession = JSON.stringify(telemetrySession)
        }
    }


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

                // Store the sensor data
                storeData(data)
            }, 
            error: function (request, status, error) {
                console.error(request.responseText)
            },
        })

        setTimeout(loop, 5000)
    }

    loop()
})